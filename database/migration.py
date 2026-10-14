"""Idempotent schema migrations for the project databases."""

import sqlite3
from typing import Set

from database.connection import get_connection

DIFFICULTY_SEED = (
    (1, "Easy"),
    (2, "Medium"),
    (3, "Hard"),
    (4, "Very Hard"),
    (5, "Ultra Hard"),
)

DIFFICULTY_ID_EXPRESSION = """
    CASE LOWER(COALESCE(difficulty, ''))
        WHEN 'easy' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'hard' THEN 3
        WHEN 'very hard' THEN 4
        WHEN 'ultra hard' THEN 5
        WHEN 'nível 1' THEN 1
        WHEN 'nivel 1' THEN 1
        WHEN 'nível 2' THEN 2
        WHEN 'nivel 2' THEN 2
        WHEN 'nível 3' THEN 3
        WHEN 'nivel 3' THEN 3
        WHEN 'nível 4' THEN 4
        WHEN 'nivel 4' THEN 4
        WHEN 'nível 5' THEN 5
        WHEN 'nivel 5' THEN 5
        ELSE NULL
    END
"""

BASE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS "advantages" (
        "advantage_id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "name" TEXT NOT NULL,
        "cost" INTEGER DEFAULT 0,
        "description" TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "disadvantages" (
        "disadvantage_id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "name" TEXT NOT NULL,
        "cost" INTEGER DEFAULT 0,
        "description" TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "difficulties" (
        "difficulty_id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "difficulty" TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "character_advantages" (
        "character_advantage_id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "character_id" INTEGER NOT NULL,
        "advantage_id" INTEGER NOT NULL,
        "notes" TEXT,
        UNIQUE("character_id", "advantage_id"),
        FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
        FOREIGN KEY("advantage_id") REFERENCES "advantages"("advantage_id") ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "character_disadvantages" (
        "character_disadvantage_id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "character_id" INTEGER NOT NULL,
        "disadvantage_id" INTEGER NOT NULL,
        "notes" TEXT,
        UNIQUE("character_id", "disadvantage_id"),
        FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
        FOREIGN KEY("disadvantage_id") REFERENCES "disadvantages"("disadvantage_id") ON DELETE CASCADE
    )
    """,
)


def _table_columns(connection: sqlite3.Connection, table: str) -> Set[str]:
    """Returns the set of column names declared for a table."""
    rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    return {row[1] for row in rows}


def _migrate_skills_difficulty(connection: sqlite3.Connection) -> None:
    """Rebuilds skills replacing the text difficulty column with the FK column."""
    connection.execute(
        """
        CREATE TABLE "skills_new" (
            "skill_id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "name" TEXT,
            "attribute" TEXT,
            "difficulty_id" INTEGER,
            "description" TEXT,
            FOREIGN KEY("difficulty_id") REFERENCES "difficulties"("difficulty_id")
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO "skills_new" ("skill_id", "name", "attribute", "difficulty_id", "description")
        SELECT "skill_id", "name", "attribute", {DIFFICULTY_ID_EXPRESSION}, "description"
        FROM "skills"
        """
    )
    connection.execute('DROP TABLE "skills"')
    connection.execute('ALTER TABLE "skills_new" RENAME TO "skills"')


def _migrate_spells_difficulty(connection: sqlite3.Connection) -> None:
    """Rebuilds spells replacing the text difficulty column with the FK column."""
    connection.execute(
        """
        CREATE TABLE "spells_new" (
            "spell_id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "name" TEXT,
            "attribute" TEXT,
            "class" INTEGER,
            "difficulty_id" INTEGER,
            "cost" INTEGER,
            "resource" TEXT,
            "description" TEXT,
            FOREIGN KEY("class") REFERENCES "spell_classes"("spell_class_id"),
            FOREIGN KEY("difficulty_id") REFERENCES "difficulties"("difficulty_id")
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO "spells_new" ("spell_id", "name", "attribute", "class", "difficulty_id", "cost", "resource", "description")
        SELECT "spell_id", "name", "attribute", "class", {DIFFICULTY_ID_EXPRESSION}, "cost", "resource", "description"
        FROM "spells"
        """
    )
    connection.execute('DROP TABLE "spells"')
    connection.execute('ALTER TABLE "spells_new" RENAME TO "spells"')


def _migrate_trait_relation(
    connection: sqlite3.Connection,
    table: str,
    id_column: str,
    fk_column: str,
    referenced_table: str,
    referenced_column: str,
) -> None:
    """Drops the legacy levels column from character trait relation tables."""
    if "levels" not in _table_columns(connection, table):
        return

    new_table = f"{table}_new"
    connection.execute(
        f"""
        CREATE TABLE "{new_table}" (
            "{id_column}" INTEGER PRIMARY KEY AUTOINCREMENT,
            "character_id" INTEGER NOT NULL,
            "{fk_column}" INTEGER NOT NULL,
            "notes" TEXT,
            UNIQUE("character_id", "{fk_column}"),
            FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
            FOREIGN KEY("{fk_column}") REFERENCES "{referenced_table}"("{referenced_column}") ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO "{new_table}" ("{id_column}", "character_id", "{fk_column}", "notes")
        SELECT "{id_column}", "character_id", "{fk_column}", "notes" FROM "{table}"
        """
    )
    connection.execute(f'DROP TABLE "{table}"')
    connection.execute(f'ALTER TABLE "{new_table}" RENAME TO "{table}"')


def apply_migrations(path=None) -> None:
    """Creates and normalizes every table required by the planner. Safe to run repeatedly."""
    connection = get_connection(path)
    try:
        connection.isolation_level = None
        connection.execute("PRAGMA foreign_keys = OFF;")

        for statement in BASE_STATEMENTS:
            connection.execute(statement)

        for difficulty_id, label in DIFFICULTY_SEED:
            connection.execute(
                "INSERT OR IGNORE INTO difficulties (difficulty_id, difficulty) VALUES (?, ?)",
                (difficulty_id, label),
            )

        if "difficulty" in _table_columns(connection, "skills"):
            _migrate_skills_difficulty(connection)

        if "difficulty" in _table_columns(connection, "spells"):
            _migrate_spells_difficulty(connection)

        _migrate_trait_relation(
            connection,
            "character_advantages",
            "character_advantage_id",
            "advantage_id",
            "advantages",
            "advantage_id",
        )
        _migrate_trait_relation(
            connection,
            "character_disadvantages",
            "character_disadvantage_id",
            "disadvantage_id",
            "disadvantages",
            "disadvantage_id",
        )

        connection.execute("PRAGMA foreign_keys = ON;")
        violations = connection.execute("PRAGMA foreign_key_check;").fetchall()
        if violations:
            raise RuntimeError(
                f"Foreign key violations detected after migration: {violations}"
            )
    finally:
        connection.close()
