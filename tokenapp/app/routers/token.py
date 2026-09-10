from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import TokenRecord
from app.schemas import RefreshResult, TokenStatus
from app.token_manager import _mask, token_manager

router = APIRouter(prefix="/token", tags=["token"])


def _to_status(record: TokenRecord | None) -> TokenStatus:
    if record is None:
        return TokenStatus(has_token=False)
    seconds_left = (record.expires_at - datetime.now(timezone.utc)).total_seconds()
    return TokenStatus(
        has_token=True,
        token_type=record.token_type,
        expires_at=record.expires_at,
        seconds_until_expiry=max(seconds_left, 0),
        access_token_preview=_mask(record.access_token),
    )


@router.get("/status", response_model=TokenStatus)
async def get_status(db: AsyncSession = Depends(get_db)) -> TokenStatus:
    """Show the current cached token's state (masked — never the full token)."""
    record = await token_manager.get_current_record(db)
    return _to_status(record)


@router.post("/refresh", response_model=RefreshResult)
async def force_refresh(db: AsyncSession = Depends(get_db)) -> RefreshResult:
    """Force an immediate token refresh from the third-party provider."""
    record = await token_manager.refresh(db)
    return RefreshResult(refreshed=True, message="Token refreshed successfully.", status=_to_status(record))
