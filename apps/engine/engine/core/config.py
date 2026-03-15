"""Application configuration via environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Engine configuration loaded from environment variables."""

    # Application
    app_name: str = "subtensor-labs-engine"
    debug: bool = False
    # Binds all interfaces — expected for Docker; restrict in bare-metal deploys
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/subtensor_labs"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20

    # Bittensor
    subtensor_network: str = "finney"
    subtensor_endpoint: str = ""
    metagraph_sync_interval_seconds: int = 120
    metagraph_sync_workers: int = 8
    price_sync_interval_seconds: int = 120
    price_sync_workers: int = 8
    price_sync_timeout_seconds: int = 30

    # Cache TTLs (seconds) — defaults synchronized with packages/shared/constants.ts CACHE_TTL
    cache_ttl_metagraph: int = 180
    cache_ttl_price: int = 180
    cache_ttl_portfolio: int = 300
    cache_ttl_screener: int = 120

    # Taostats
    taostats_api_url: str = "https://api.taostats.io"
    taostats_api_key: str = ""
    taostats_backfill_hour_utc: int = 3
    taostats_backfill_workers: int = 2
    taostats_request_timeout_seconds: int = 30
    taostats_backfill_batch_size: int = 200
    taostats_rate_limit_max_retries: int = 5

    # Security
    address_encryption_key: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_prefix": "ENGINE_", "env_file": ".env", "case_sensitive": False}

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate security-critical settings in non-debug mode."""
        if not self.debug:
            if not self.address_encryption_key:
                raise ValueError(
                    "ENGINE_ADDRESS_ENCRYPTION_KEY must be set in production. "
                    "Set ENGINE_DEBUG=true for local development without encryption."
                )
            if not self.taostats_api_key:
                raise ValueError(
                    "ENGINE_TAOSTATS_API_KEY must be set in production. "
                    "Set ENGINE_DEBUG=true for local development without Taostats backfill."
                )
            if "*" in self.cors_origins:
                raise ValueError(
                    "ENGINE_CORS_ORIGINS must not contain '*' in production. "
                    "Specify explicit allowed origins."
                )
        return self


settings = Settings()
