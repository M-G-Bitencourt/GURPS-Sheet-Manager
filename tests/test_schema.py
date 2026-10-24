import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.connection import initialize_database, validate_database


class SchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "gurps.db"

    def tearDown(self):
        self.temporary.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def test_initialize_creates_expected_schema_and_seeds(self):
        initialize_database(self.database_path)

        self.assertEqual(validate_database(self.database_path), [])

        connection = self.connect()
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(version, 13)

            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            for table in (
                "hit_locations",
                "damage_types",
                "weapons",
                "weapon_modes",
                "character_weapons",
                "combat_sessions",
                "pending_attacks",
                "combat_effects",
                "character_combat_effects",
                "combat_participants",
                "combat_log",
                "guild_settings",
            ):
                self.assertIn(table, tables)
            for legacy_table in (
                "melee_weapons",
                "melee_weapon_modes",
                "ranged_weapons",
                "character_melee_weapons",
                "character_ranged_weapons",
            ):
                self.assertNotIn(legacy_table, tables)

            pending_attack_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(pending_attacks)")
            }
            self.assertIn("hit_sublocation", pending_attack_columns)
            self.assertIn("hit_sublocation_roll", pending_attack_columns)
            self.assertIn("armor_divisor", pending_attack_columns)

            mode_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(weapon_modes)")
            }
            self.assertIn("skill_id", mode_columns)
            self.assertIn("attack_kind", mode_columns)
            self.assertIn("damage_dice", mode_columns)
            self.assertIn("damage_type_id", mode_columns)
            self.assertIn("armor_divisor", mode_columns)
            self.assertNotIn("damage_type", mode_columns)
            self.assertNotIn("melee_weapon_id", mode_columns)

            character_weapon_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(character_weapons)"
                )
            }
            self.assertIn("current_shots", character_weapon_columns)

            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM hit_locations"
                ).fetchone()[0],
                11,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM skills WHERE name = 'Briga'"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM damage_types"
                ).fetchone()[0],
                13,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM weapons "
                    "WHERE is_unarmed = 1 AND is_fallback = 1"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM weapon_modes WHERE skill_id IS NULL"
                ).fetchone()[0],
                2,
            )
        finally:
            connection.close()

    def test_initialize_is_safe_to_repeat(self):
        initialize_database(self.database_path)
        initialize_database(self.database_path)

        connection = self.connect()
        try:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM skills").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM hit_locations"
                ).fetchone()[0],
                11,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM damage_types"
                ).fetchone()[0],
                13,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM weapons"
                ).fetchone()[0],
                2,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM weapon_modes"
                ).fetchone()[0],
                4,
            )
        finally:
            connection.close()

    def test_validate_rejects_legacy_version(self):
        initialize_database(self.database_path)

        connection = self.connect()
        try:
            connection.execute("PRAGMA user_version = 0")
            connection.commit()
        finally:
            connection.close()

        problems = validate_database(self.database_path)
        self.assertTrue(any("Versão de esquema incompatível" in item for item in problems))

    def test_validate_rejects_missing_table_and_column(self):
        initialize_database(self.database_path)

        connection = self.connect()
        try:
            connection.execute("DROP TABLE hit_locations")
            connection.execute(
                "ALTER TABLE weapon_modes "
                "RENAME COLUMN armor_divisor TO armor_divisor_old"
            )
            connection.commit()
        finally:
            connection.close()

        problems = validate_database(self.database_path)
        self.assertTrue(any("hit_locations" in item for item in problems))
        self.assertTrue(any("armor_divisor" in item for item in problems))


if __name__ == "__main__":
    unittest.main()
