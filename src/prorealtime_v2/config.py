from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TradingLimits:
    max_orders_per_run: int = 5
    max_notional_per_order: float = 1500.0


@dataclass(frozen=True)
class EmailConfig:
    host: str
    port: int
    user: str | None
    app_password: str | None
    recipient: str | None

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.port and self.user and self.app_password and self.recipient)


@dataclass(frozen=True)
class Settings:
    root: Path
    data_dir: Path
    signals_dir: Path
    log_level: str
    email: EmailConfig
    limits: TradingLimits
    trading_mode: str

    @property
    def dry_run(self) -> bool:
        return self.trading_mode != "live"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw in (None, "") else int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw in (None, "") else float(raw)


def load_settings() -> Settings:
    root = Path(os.getenv("PROREALTIME_ROOT", ".")).expanduser().resolve()
    data_dir = Path(os.getenv("PROREALTIME_DATA_DIR", root / "data")).expanduser()
    signals_dir = Path(os.getenv("PROREALTIME_SIGNALS_DIR", root / "reports")).expanduser()
    return Settings(
        root=root,
        data_dir=data_dir if data_dir.is_absolute() else root / data_dir,
        signals_dir=signals_dir if signals_dir.is_absolute() else root / signals_dir,
        log_level=os.getenv("PROREALTIME_LOG_LEVEL", "INFO").upper(),
        trading_mode=os.getenv("PROREALTIME_TRADING_MODE", "dry-run").lower(),
        limits=TradingLimits(
            max_orders_per_run=_env_int("PROREALTIME_MAX_ORDERS_PER_RUN", 5),
            max_notional_per_order=_env_float("PROREALTIME_MAX_NOTIONAL_PER_ORDER", 1500.0),
        ),
        email=EmailConfig(
            host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            port=_env_int("SMTP_PORT", 587),
            user=os.getenv("SMTP_USER") or None,
            app_password=os.getenv("SMTP_APP_PASSWORD") or None,
            recipient=os.getenv("SMTP_TO") or None,
        ),
    )
