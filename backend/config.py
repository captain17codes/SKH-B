"""
Configuration settings for Kopargaon CRPP MVP
Block 1 - Backend Lead Dev
"""
import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Kopargaon CRPP API"
    APP_VERSION: str = "0.1.0-MVP"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./kopargaon_crpp.db"
    )

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mvp-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    ALGORITHM: str = "HS256"

    # WhatsApp Business API (Block 3 will fill these)
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_ACCESS_TOKEN: Optional[str] = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: Optional[str] = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
    WHATSAPP_API_VERSION: str = os.getenv("WHATSAPP_API_VERSION", "v20.0")

    # Meta Graph API base URL
    @property
    def WHATSAPP_API_URL(self) -> str:
        return f"https://graph.facebook.com/{self.WHATSAPP_API_VERSION}"

    # Notification settings
    WHATSAPP_TEMPLATE_NAMESPACE: Optional[str] = os.getenv("WHATSAPP_TEMPLATE_NAMESPACE")
    ENABLE_NOTIFICATIONS: bool = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"

    # Deduplication settings
    DEDUPE_HAMMING_THRESHOLD: int = int(os.getenv("DEDUPE_HAMMING_THRESHOLD", "10"))
    DEDUPE_RADIUS_METERS: int = int(os.getenv("DEDUPE_RADIUS_METERS", "150"))

    # Triage settings
    DEFAULT_DAILY_BUDGET: float = float(os.getenv("DEFAULT_DAILY_BUDGET", "100000"))  # ₹100,000
    DEFAULT_DAILY_WORKFORCE_HOURS: float = float(os.getenv("DEFAULT_DAILY_WORKFORCE_HOURS", "80"))

    # File uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

    # CORS
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

    # RTS SLA days by category (Phase 2+)
    SLA_DAYS: dict = {
        "critical": 1,      # Emergency
        "urgent": 7,        # High priority
        "normal": 21,       # Standard per RTS Act
        "low": 45           # Lower priority
    }


# Global settings instance
settings = Settings()
