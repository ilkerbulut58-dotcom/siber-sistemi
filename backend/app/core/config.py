"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, RedisDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SIBER"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://siber:siber@localhost:5432/siber"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # CORS
    cors_origins: Annotated[list[str], NoDecode] = Field(default=["http://localhost:3000"])
    trusted_proxy_ips: Annotated[list[str], NoDecode] = Field(default=[])
    # Security (Phase 2+)
    secret_key: str = Field(default="change-me-in-production-use-openssl-rand")
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    rate_limit_enabled: bool = False
    auth_rate_limit_per_minute: int = Field(default=10, ge=1, le=1_000)
    upload_rate_limit_per_hour: int = Field(default=20, ge=1, le=10_000)
    retest_rate_limit_per_hour: int = Field(default=30, ge=1, le=10_000)
    scan_rate_limit_per_hour: int = Field(default=20, ge=1, le=10_000)
    scan_concurrency_limit: int = Field(default=2, ge=1, le=20)
    scan_daily_quota: int = Field(default=50, ge=1, le=10_000)
    notifications_provider: Literal["noop"] = Field(
        default="noop",
        description="Notification delivery backend (noop logs only during closed pilot)",
    )
    scan_max_duration_seconds: int = Field(default=600, ge=60, le=7200)
    scan_max_redirects: int = Field(default=5, ge=0, le=20)
    scan_max_response_bytes: int = Field(default=2_000_000, ge=10_000, le=50_000_000)

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # Testing / development shortcuts
    skip_domain_verification: bool = Field(
        default=False,
        description="Skip DNS/hostname checks and auto-verify domains for testing",
    )
    use_celery_for_scans: bool = Field(
        default=False,
        description="Enqueue scan jobs on Celery worker instead of FastAPI background tasks",
    )
    zap_api_url: str = Field(
        default="http://localhost:8080",
        description="OWASP ZAP daemon API base URL",
    )
    zap_enabled: bool = Field(
        default=True,
        description="Enable ZAP passive scanning when the daemon is reachable",
    )
    zap_passive_wait_seconds: int = Field(
        default=45,
        description="Max seconds to wait for ZAP passive scan queue to drain",
    )
    zap_spider_wait_seconds: int = Field(
        default=60,
        description="Max seconds to wait for ZAP spider (deep profile)",
    )
    zap_scan_timeout_seconds: int = Field(
        default=90,
        description="Hard timeout for entire ZAP passive scan session",
    )
    nuclei_timeout_seconds: int = Field(
        default=90,
        description="Max seconds for a Nuclei subprocess run",
    )
    scan_timeout_safe_seconds: int = Field(
        default=120,
        description="Overall timeout for safe profile scanners (parallel)",
    )
    scan_timeout_deep_seconds: int = Field(
        default=240,
        description="Overall timeout for deep profile scanners (parallel)",
    )
    scan_timeout_code_seconds: int = Field(
        default=90,
        description="Overall timeout for code profile scanners (parallel)",
    )
    scan_stale_minutes: int = Field(
        default=12,
        description="Mark scans stuck in active states as failed after this many minutes",
    )

    # AI / LLM (Phase 8)
    ai_enabled: bool = Field(
        default=False,
        description="Enable LLM enrichment for findings after scan completion",
    )
    ai_provider: Literal["openai"] = Field(
        default="openai",
        description="AI provider adapter to use",
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI (or compatible) API key",
    )
    ai_model: str = Field(
        default="gpt-4o-mini",
        description="LLM model name for finding analysis",
    )
    ai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible API base URL",
    )
    ai_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout per finding LLM request",
    )
    ai_max_concurrency: int = Field(
        default=3,
        description="Max parallel LLM requests during batch enrichment",
    )

    # ASM (Phase 9)
    asm_max_subdomains: int = Field(
        default=30,
        description="Max subdomains to discover per ASM job (passive)",
    )
    asm_max_hosts_probe: int = Field(
        default=15,
        description="Max hosts to HTTP/TLS probe during ASM",
    )

    # Mobile Application Security (Phase 9B)
    mobile_max_upload_bytes: int = Field(
        default=100 * 1024 * 1024,
        description="Maximum APK upload size in bytes (default 100MB)",
    )
    mobile_storage_path: str = Field(
        default="/var/siber/mobile",
        description="Private filesystem directory for stored mobile artifacts",
    )
    mobile_analysis_timeout_seconds: int = Field(
        default=600,
        ge=30,
        le=3_600,
        description="Hard execution timeout for one isolated static mobile analysis",
    )
    mobile_artifact_retention_hours: int = Field(
        default=24,
        ge=0,
        le=24 * 365,
        description="Hours to retain a private APK artifact after analysis; zero deletes it immediately",
    )
    mobile_analysis_queue: str = "mobile"

    # Detection Quality & Benchmark Lab. Disabled outside explicitly configured CI/lab runs.
    benchmark_gate_mode: Literal["off", "report", "enforce"] = "off"
    benchmark_min_recall: float = Field(default=0.90, ge=0, le=1)
    benchmark_max_false_positive_rate: float = Field(default=0.20, ge=0, le=1)
    benchmark_recall_drop_limit: float = Field(default=0.05, ge=0, le=1)
    benchmark_max_duration_seconds: int = Field(default=300, ge=1)
    benchmark_fail_on_duration: bool = False
    benchmark_storage_path: str = Field(
        default="/var/siber/benchmark",
        description="Isolated storage for benchmark APK artifacts (not customer upload path)",
    )
    benchmark_ca_cert_path: str = Field(
        default="",
        description="Optional PEM bundle for trusting pinned realistic benchmark TLS certificates",
    )
    benchmark_active_realistic_enabled: bool = Field(
        default=False,
        description="Gate for active realistic suites (phase 11.3); auto-enabled in lab container mode",
    )
    benchmark_active_request_budget: int = Field(
        default=250,
        ge=1,
        le=5000,
        description="Maximum outbound HTTP requests per active benchmark scan",
    )
    benchmark_active_concurrency_limit: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum concurrent active scanners during benchmark lab runs",
    )
    benchmark_active_timeout_seconds: int = Field(
        default=180,
        ge=30,
        le=900,
        description="Hard timeout for active benchmark scan profiles",
    )
    benchmark_realistic_startup_seconds: int = Field(default=120, ge=30, le=600)
    benchmark_realistic_suite_timeout_seconds: int = Field(default=90, ge=30, le=600)
    benchmark_realistic_active_suite_timeout_seconds: int = Field(
        default=240,
        ge=60,
        le=900,
        description="Per-suite timeout for active realistic benchmark runs",
    )
    benchmark_realistic_job_timeout_seconds: int = Field(default=300, ge=60, le=3600)
    benchmark_realistic_active_job_timeout_seconds: int = Field(
        default=600,
        ge=120,
        le=3600,
        description="Overall timeout for active realistic benchmark jobs",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("trusted_proxy_ips", mode="before")
    @classmethod
    def parse_trusted_proxy_ips(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [address.strip() for address in value.split(",") if address.strip()]
        return value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
