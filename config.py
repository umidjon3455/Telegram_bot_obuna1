import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(value.strip())
        for value in os.getenv("ADMIN_IDS", "").split(",")
        if value.strip()
    ])
    REQUIRED_CHANNELS: List[str] = field(default_factory=lambda: [
        value.strip()
        for value in os.getenv("REQUIRED_CHANNELS", "").split(",")
        if value.strip()
    ])
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/telegram_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    USE_WEBHOOK: bool = os.getenv("USE_WEBHOOK", "false").lower() == "true"
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    SPAM_RATE_LIMIT: int = int(os.getenv("SPAM_RATE_LIMIT", "5"))
    SPAM_RATE_WINDOW: int = int(os.getenv("SPAM_RATE_WINDOW", "10"))
    REFERRAL_BONUS: int = int(os.getenv("REFERRAL_BONUS", "1"))
    BROADCAST_DELAY: float = float(os.getenv("BROADCAST_DELAY", "0.05"))

    def validate(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set.")
        if len(self.REQUIRED_CHANNELS) != 3:
            raise ValueError("Exactly 3 REQUIRED_CHANNELS must be configured, separated by commas.")
        if not self.REDIS_URL:
            raise ValueError("REDIS_URL is required for Redis FSM storage and caching.")
        return self


config = Config().validate()
