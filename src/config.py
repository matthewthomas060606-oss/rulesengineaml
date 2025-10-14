from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from functools import lru_cache

def _env(name: str, default=None, cast=str):
    val = os.getenv(name, default)
    if val is None:
        return None
    if cast is bool:
        return str(val).strip().lower() in {"1", "true", "yes", "on"}
    if cast in (int, float):
        try:
            return cast(val)
        except Exception:
            return cast(default) if default is not None else None
    return str(val)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(_env("AML_DATA_DIR", str(BASE_DIR / "data")))
DB_PATH  = Path(_env("AML_DB_PATH",   str(DATA_DIR / "sanctions.db")))
GUI_PATH = Path(_env("AML_GUI_PATH",  str(BASE_DIR / "iso-viewer" / "public")))

@dataclass(frozen=True)
class ApiConfig:
    host: str = _env("AML_API_HOST", "0.0.0.0")
    port: int = _env("AML_API_PORT", 8000, int)
    debug: bool = _env("AML_DEBUG", False, bool)

@dataclass(frozen=True)
class SecurityConfig:
    admin_key: str = _env("AML_ADMIN_KEY", "dev-key")

@dataclass(frozen=True)
class PathsConfig:
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    DB_PATH: Path = DB_PATH
    GUI_PATH: Path = GUI_PATH 

@dataclass
class ScreeningConfig:
    #change to True to include slight matches (score lower than 20) that the engine has found in the JSON response. Adds a lot more matches and most of them aren't helpful
    SHOW_SLIGHT_MATCHES: bool = _env("SHOW_SLIGHT_MATCHES", True, cast=bool)

@dataclass(frozen=True)
class AppConfig:
    api: "ApiConfig" = field(default_factory=lambda: ApiConfig())
    security: "SecurityConfig" = field(default_factory=lambda: SecurityConfig())
    paths: "PathsConfig" = field(default_factory=lambda: PathsConfig())
    screening: "ScreeningConfig" = field(default_factory=lambda: ScreeningConfig())

@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()

config = get_config()
