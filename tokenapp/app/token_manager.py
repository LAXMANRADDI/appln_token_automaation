import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import TokenRecord

logger = logging.getLogger("token_manager")


class TokenFetchError(RuntimeError):
    pass


def _mask(token: str) -> str:
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}...{token[-4:]}"


class TokenManager:
    """
    Handles fetching, caching, and auto-refreshing an OAuth2
    client_credentials access token from a third-party API.
    """

    def __init__(self) -> None:
        self._lock_key = "token_manager"  # placeholder if you add distributed locking later

    async def _fetch_from_provider(self) -> dict:
        """Call the OAuth2 token endpoint using the client_credentials grant."""
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.oauth_client_id,
            "client_secret": settings.oauth_client_secret,
        }
        if settings.oauth_scope:
            data["scope"] = settings.oauth_scope

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(settings.oauth_token_url, data=data)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("Token fetch failed: %s", exc)
                raise TokenFetchError(str(exc)) from exc

        payload = resp.json()
        if "access_token" not in payload:
            raise TokenFetchError(f"Provider response missing access_token: {payload}")
        return payload

    async def get_current_record(self, session: AsyncSession) -> TokenRecord | None:
        result = await session.execute(
            select(TokenRecord).where(TokenRecord.is_current.is_(True)).order_by(TokenRecord.id.desc())
        )
        return result.scalars().first()

    def _needs_refresh(self, record: TokenRecord | None) -> bool:
        if record is None:
            return True
        margin = timedelta(seconds=settings.token_refresh_margin_seconds)
        return datetime.now(timezone.utc) >= (record.expires_at - margin)

    async def refresh(self, session: AsyncSession) -> TokenRecord:
        """Force-fetch a new token from the provider and persist it as current."""
        payload = await self._fetch_from_provider()

        expires_in = int(payload.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Mark any existing record(s) as no longer current
        await session.execute(update(TokenRecord).values(is_current=False))

        record = TokenRecord(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "Bearer"),
            expires_at=expires_at,
            is_current=True,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

        logger.info(
            "Refreshed token. New token %s expires at %s",
            _mask(record.access_token),
            record.expires_at.isoformat(),
        )
        return record

    async def get_valid_token(self, session: AsyncSession) -> TokenRecord:
        """
        Return a currently-valid token, refreshing it first if it's
        missing, expired, or within the refresh margin of expiring.
        """
        record = await self.get_current_record(session)
        if self._needs_refresh(record):
            record = await self.refresh(session)
        return record

    async def check_and_refresh_if_needed(self, session: AsyncSession) -> bool:
        """Used by the background scheduler. Returns True if a refresh happened."""
        record = await self.get_current_record(session)
        if self._needs_refresh(record):
            await self.refresh(session)
            return True
        return False


token_manager = TokenManager()
