import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # ── Bot ───────────────────────────────────────────────
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])
    REQUIRED_CHANNELS: List[str] = field(default_factory=lambda: [
        x.strip() for x in os.getenv("REQUIRED_CHANNELS", "@").split(",") if x.strip()
    ])

    # ── PostgreSQL ────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:1234/telegram_db"
    )

    # ── Redis ─────────────────────────────────────────────
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # ── Webhook ───────────────────────────────────────────
    USE_WEBHOOK: bool = os.getenv("USE_WEBHOOK", "false").lower() == "true"
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))

    # ── Anti-spam ─────────────────────────────────────────
    SPAM_RATE_LIMIT: int = int(os.getenv("SPAM_RATE_LIMIT", "5"))
    SPAM_RATE_WINDOW: int = int(os.getenv("SPAM_RATE_WINDOW", "10"))

    # ── Referral ──────────────────────────────────────────
    REFERRAL_BONUS: int = int(os.getenv("REFERRAL_BONUS", "1"))  # bonus points per referral

    # ── Broadcast ─────────────────────────────────────────
    BROADCAST_DELAY: float = float(os.getenv("BROADCAST_DELAY", "0.05"))  # seconds between sends

    def validate(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set!")
        if len(self.REQUIRED_CHANNELS) != 1:
            raise ValueError("Exactly 3 REQUIRED_CHANNELS must be configured!")
        return self


config = Config().validate()
