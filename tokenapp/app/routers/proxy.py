import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.token_manager import token_manager

router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.get("/call")
async def call_external_api(path: str = "", db: AsyncSession = Depends(get_db)) -> dict:
    """
    Example endpoint: uses the auto-refreshed token to call the
    third-party API on the caller's behalf. `path` is appended to
    EXTERNAL_API_BASE_URL, e.g. /proxy/call?path=users/me
    """
    record = await token_manager.get_valid_token(db)
    url = f"{settings.external_api_base_url.rstrip('/')}/{path.lstrip('/')}"

    headers = {"Authorization": f"{record.token_type} {record.access_token}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream call failed: {exc}") from exc

    return {
        "upstream_status": resp.status_code,
        "upstream_url": url,
        "body": _safe_json(resp),
    }


def _safe_json(resp: httpx.Response):
    try:
        return resp.json()
    except ValueError:
        return resp.text
