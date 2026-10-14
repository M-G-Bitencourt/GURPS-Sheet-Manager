"""SQLite connection factory bound to a configurable database file."""

import sqlite3
import threading
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "database.db"
INIT_SQL_PATH = PROJECT_ROOT / "data" / "init.sql"

_path_lock = threading.Lock()
_database_path = DEFAULT_DATABASE_PATH


def _resolve_target(path=None) -> Path:
    """Resolves an explicit path or falls back to the active database."""
    if path is None:
        return get_database_path()
    return Path(path).expanduser().resolve()


def get_database_path() -> Path:
    """Returns the path of the database currently in use."""
    with _path_lock:
        return _database_path


def set_database_path(path) -> Path:
    """Switches the active database file used by every new connection."""
    global _database_path
    resolved = Path(path).expanduser().resolve()
    with _path_lock:
        _database_path = resolved
    return resolved


def get_connection(path=None) -> sqlite3.Connection:
    """
    Builds a fresh SQLite connection with foreign keys enabled and
    dictionary-like row access. Callers own the connection lifecycle.
    """
    connection = sqlite3.connect(_resolve_target(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def database_exists(path=None) -> bool:
    """Reports whether the database file is present on disk."""
    return _resolve_target(path).exists()


def initialize_database(path=None) -> None:
    """
    Validates the existence of the SQLite binary file. If absent, it builds
    the database dynamically by executing the DDL instructions from init.sql.
    """
    target = _resolve_target(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        return

    if not INIT_SQL_PATH.exists():
        raise FileNotFoundError(
            f"Initialization aborted: the required DDL script '{INIT_SQL_PATH}' "
            "is missing from the filesystem."
        )

    schema_instructions = INIT_SQL_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(schema_instructions)
        connection.commit()


def _required_tables() -> dict:
    """Maps every app-managed table to the columns the application expects."""
    from api.resources import RELATIONS, RESOURCES

    required = {}
    for resource in RESOURCES.values():
        columns = required.setdefault(resource.table, set())
        columns.update(column.name for column in resource.columns)
    for relation in RELATIONS.values():
        columns = required.setdefault(relation.table, set())
        columns.add("character_id")
        columns.add(relation.item_fk)
        columns.update(column.name for column in relation.columns)
        if relation.secondary_fk:
            columns.add(relation.secondary_fk)
    return required


def validate_database(path=None) -> List[str]:
    """
    Inspects a database file without modifying it. Returns a list of problems;
    an empty list means the file is a compatible GURPS-Sheet-Manager database.
    """
    target = _resolve_target(path)

    if not target.is_file():
        return [f"Arquivo não encontrado: {target}"]

    with target.open("rb") as handle:
        header = handle.read(16)

    if header != b"SQLite format 3\x00":
        return ["O arquivo selecionado não é um banco SQLite válido."]

    required = _required_tables()
    problems = []

    try:
        connection = sqlite3.connect(f"{target.as_uri()}?mode=ro", uri=True)
        try:
            connection.execute("PRAGMA query_only = ON;")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            missing_tables = sorted(table for table in required if table not in tables)
            if missing_tables:
                problems.append("Tabelas ausentes: " + ", ".join(missing_tables) + ".")

            for table in sorted(required):
                if table in missing_tables:
                    continue
                existing = {
                    row[1]
                    for row in connection.execute(f'PRAGMA table_info("{table}")')
                }
                missing_columns = sorted(required[table] - existing)
                if missing_columns:
                    problems.append(
                        f'Colunas ausentes em "{table}": ' + ", ".join(missing_columns) + "."
                    )
        finally:
            connection.close()
    except sqlite3.DatabaseError as error:
        problems.append(f"Falha ao ler o banco de dados: {error}")

    return problems
