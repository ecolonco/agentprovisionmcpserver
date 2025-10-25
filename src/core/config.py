"""
Configuration management for MCP Server
Uses Pydantic Settings for environment variable management
"""
from typing import List, Optional
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ============================================
    # Application Settings
    # ============================================
    APP_NAME: str = "MCP Server"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ============================================
    # API Settings
    # ============================================
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # ============================================
    # Security
    # ============================================
    SECRET_KEY: str = Field(..., description="Secret key for JWT signing")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ============================================
    # Database Configuration
    # ============================================
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection string"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # ============================================
    # Redis Configuration
    # ============================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50

    # ============================================
    # Kafka Configuration
    # ============================================
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PREFIX: str = "mcp"
    KAFKA_CONSUMER_GROUP: str = "mcp-server"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"

    # ============================================
    # Temporal Configuration
    # ============================================
    TEMPORAL_HOST: str = "localhost"
    TEMPORAL_PORT: int = 7233
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "mcp-tasks"

    # ============================================
    # Integration Credentials - ADP
    # ============================================
    ADP_CLIENT_ID: Optional[str] = None
    ADP_CLIENT_SECRET: Optional[str] = None
    ADP_API_BASE_URL: str = "https://api.adp.com"
    ADP_AUTH_URL: str = "https://accounts.adp.com/auth/oauth/v2/token"

    # ============================================
    # Integration Credentials - Eaglesoft
    # ============================================
    EAGLESOFT_API_KEY: Optional[str] = None
    EAGLESOFT_API_BASE_URL: str = "https://api.eaglesoft.com"
    EAGLESOFT_TENANT_ID: Optional[str] = None

    # ============================================
    # Integration Credentials - DentalIntel
    # ============================================
    DENTALINTEL_API_KEY: Optional[str] = None
    DENTALINTEL_API_BASE_URL: str = "https://api.dentalintel.com"
    DENTALINTEL_PRACTICE_ID: Optional[str] = None

    # ============================================
    # Integration Credentials - NetSuite
    # ============================================
    NETSUITE_ACCOUNT_ID: Optional[str] = None
    NETSUITE_CONSUMER_KEY: Optional[str] = None
    NETSUITE_CONSUMER_SECRET: Optional[str] = None
    NETSUITE_TOKEN_ID: Optional[str] = None
    NETSUITE_TOKEN_SECRET: Optional[str] = None
    NETSUITE_API_BASE_URL: Optional[str] = None

    # ============================================
    # Integration Credentials - Bank/Merchant
    # ============================================
    MERCHANT_PROCESSOR_API_KEY: Optional[str] = None
    MERCHANT_PROCESSOR_API_BASE_URL: str = "https://api.merchantprocessor.com"

    # ============================================
    # Observability
    # ============================================
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "mcp-server"

    # ============================================
    # CORS Settings
    # ============================================
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    CORS_ALLOW_CREDENTIALS: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ============================================
    # Rate Limiting
    # ============================================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # ============================================
    # Sync Settings
    # ============================================
    DEFAULT_SYNC_BATCH_SIZE: int = 100
    DEFAULT_SYNC_TIMEOUT_SECONDS: int = 300
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BACKOFF_SECONDS: int = 5

    # ============================================
    # Data Retention
    # ============================================
    AUDIT_LOG_RETENTION_DAYS: int = 90
    JOB_HISTORY_RETENTION_DAYS: int = 30

    # ============================================
    # AWS/Cloud Settings
    # ============================================
    AWS_REGION: str = "us-east-1"
    AWS_ACCOUNT_ID: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    ECS_CLUSTER_NAME: Optional[str] = None
    RDS_INSTANCE_CLASS: str = "db.t3.medium"

    # ============================================
    # Computed Properties
    # ============================================

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def temporal_address(self) -> str:
        """Get Temporal server address"""
        return f"{self.TEMPORAL_HOST}:{self.TEMPORAL_PORT}"

    @property
    def kafka_servers_list(self) -> List[str]:
        """Get Kafka servers as list"""
        return [server.strip() for server in self.KAFKA_BOOTSTRAP_SERVERS.split(",")]


# ============================================
# Global Settings Instance
# ============================================

settings = Settings()


# ============================================
# Helper Functions
# ============================================

def get_settings() -> Settings:
    """
    Dependency injection for FastAPI routes
    Returns the global settings instance
    """
    return settings


def get_integration_config(system: str) -> dict:
    """
    Get integration-specific configuration

    Args:
        system: Integration system name (e.g., 'adp', 'eaglesoft')

    Returns:
        Dictionary with integration configuration
    """
    system = system.lower()

    if system == "adp":
        return {
            "client_id": settings.ADP_CLIENT_ID,
            "client_secret": settings.ADP_CLIENT_SECRET,
            "api_base_url": settings.ADP_API_BASE_URL,
            "auth_url": settings.ADP_AUTH_URL,
        }
    elif system == "eaglesoft":
        return {
            "api_key": settings.EAGLESOFT_API_KEY,
            "api_base_url": settings.EAGLESOFT_API_BASE_URL,
            "tenant_id": settings.EAGLESOFT_TENANT_ID,
        }
    elif system == "dentalintel":
        return {
            "api_key": settings.DENTALINTEL_API_KEY,
            "api_base_url": settings.DENTALINTEL_API_BASE_URL,
            "practice_id": settings.DENTALINTEL_PRACTICE_ID,
        }
    elif system == "netsuite":
        return {
            "account_id": settings.NETSUITE_ACCOUNT_ID,
            "consumer_key": settings.NETSUITE_CONSUMER_KEY,
            "consumer_secret": settings.NETSUITE_CONSUMER_SECRET,
            "token_id": settings.NETSUITE_TOKEN_ID,
            "token_secret": settings.NETSUITE_TOKEN_SECRET,
            "api_base_url": settings.NETSUITE_API_BASE_URL,
        }
    elif system == "bank" or system == "merchant":
        return {
            "api_key": settings.MERCHANT_PROCESSOR_API_KEY,
            "api_base_url": settings.MERCHANT_PROCESSOR_API_BASE_URL,
        }
    else:
        raise ValueError(f"Unknown integration system: {system}")
