from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Postgres ---
    database_url: str = "postgresql+asyncpg://tokenapp:tokenapp@db:5432/tokenapp"

    # --- OAuth2 / third-party API client-credentials ---
    oauth_token_url: str = "https://example.com/oauth/token"
    oauth_client_id: str = "changeme"
    oauth_client_secret: str = "changeme"
    oauth_scope: str = ""

    # --- External API this app calls using the fetched token ---
    external_api_base_url: str = "https://example.com/api"

    # --- Refresh behavior ---
    # Refresh this many seconds *before* the token actually expires.
    token_refresh_margin_seconds: int = 60
    # How often the background scheduler checks whether a refresh is needed.
    poll_interval_seconds: int = 30

    # --- App ---
    app_name: str = "Token Automation Service"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
