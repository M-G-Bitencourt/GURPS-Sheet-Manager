"""User-level preferences persisted outside the project directory."""

import json
import os
import sys
from pathlib import Path
from typing import List, Optional

APP_DIRECTORY_NAME = "gurps-sheet-manager"
SETTINGS_FILE_NAME = "settings.json"
MAX_RECENT_DATABASES = 8


def config_directory() -> Path:
    """Returns the platform specific user configuration directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_DIRECTORY_NAME


def settings_path() -> Path:
    """Returns the full path of the settings file."""
    return config_directory() / SETTINGS_FILE_NAME


def load_settings() -> dict:
    """Reads the settings file, tolerating absence or corruption."""
    path = settings_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(settings: dict) -> None:
    """Writes the settings file atomically, creating its directory if needed."""
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def get_stored_database_path() -> Optional[Path]:
    """Returns the persisted active database path, if any."""
    value = load_settings().get("database_path")
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser()


def store_database_path(path) -> None:
    """Persists the active database path for the next application start."""
    settings = load_settings()
    settings["database_path"] = str(Path(path).expanduser().resolve())
    save_settings(settings)


def _normalized(path: str) -> str:
    return os.path.normcase(str(Path(path).expanduser()))


def get_recent_databases() -> List[str]:
    """Returns the most recently used database paths, newest first."""
    recent = load_settings().get("recent_databases")
    if not isinstance(recent, list):
        return []
    return [item for item in recent if isinstance(item, str) and item.strip()]


def push_recent_database(path) -> List[str]:
    """Moves the given path to the top of the recents list and persists it."""
    resolved = str(Path(path).expanduser().resolve())
    recent = [item for item in get_recent_databases() if _normalized(item) != _normalized(resolved)]
    recent.insert(0, resolved)
    recent = recent[:MAX_RECENT_DATABASES]
    settings = load_settings()
    settings["recent_databases"] = recent
    save_settings(settings)
    return recent


def remove_recent_database(path) -> List[str]:
    """Removes the given path from the recents list and persists it."""
    target = _normalized(str(path))
    recent = [item for item in get_recent_databases() if _normalized(item) != target]
    settings = load_settings()
    settings["recent_databases"] = recent
    save_settings(settings)
    return recent
