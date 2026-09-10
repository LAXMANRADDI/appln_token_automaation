from datetime import datetime

from pydantic import BaseModel


class TokenStatus(BaseModel):
    has_token: bool
    token_type: str | None = None
    expires_at: datetime | None = None
    seconds_until_expiry: float | None = None
    access_token_preview: str | None = None  # masked, never full token

    class Config:
        from_attributes = True


class RefreshResult(BaseModel):
    refreshed: bool
    message: str
    status: TokenStatus
