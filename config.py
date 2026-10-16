from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.agent", override=False)


class ConfigurationError(RuntimeError):
    """Raised when required agent configuration is missing or invalid."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


def _non_negative_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be numeric.") from exc
    if value < 0:
        raise ConfigurationError(f"{name} cannot be negative.")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    openrouter_api_key: str
    openrouter_model: str
    gmail_address: str
    gmail_app_password: str
    sender_name: str
    offer_description: str
    sender_signature: str
    daily_limit: int
    delay_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        model = os.getenv("OPENROUTER_MODEL", "openai/gpt-5.4-mini").strip() or "openai/gpt-5.4-mini"
        if model.startswith("openrouter/"):
            model = model.removeprefix("openrouter/")

        return cls(
            openrouter_api_key=_required("OPENROUTER_API_KEY"),
            openrouter_model=model,
            gmail_address=os.getenv("GMAIL_ADDRESS", "").strip(),
            gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip(),
            sender_name=os.getenv("OUTREACH_SENDER_NAME", "Giulia").strip() or "Giulia",
            offer_description=(
                os.getenv(
                    "OUTREACH_OFFER",
                    "I help small and mid-sized teams clean messy business data, improve reporting, "
                    "and turn it into practical dashboards and analysis.",
                ).strip()
            ),
            sender_signature=os.getenv(
                "OUTREACH_SIGNATURE",
                "",
            ).replace("\\n", "\n").strip(),
            daily_limit=_positive_int("OUTREACH_DAILY_LIMIT", 15),
            delay_seconds=_non_negative_float("OUTREACH_DELAY_SECONDS", 4.0),
        )
