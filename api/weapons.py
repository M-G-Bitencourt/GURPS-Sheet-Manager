"""Shared weapon mode queries used by catalog and character endpoints."""

import sqlite3
from typing import Any, Dict, List

from api.resources import weapon_mode_display

WEAPON_MODE_QUERY = """
SELECT m.mode_id, m.weapon_id, m.mode_name, m.skill_id, s.name AS skill_name,
       m.attack_kind, m.damage_base, m.damage_dice, m.damage_modifier,
       m.damage_type_id, dt.key AS damage_type_key, m.armor_divisor,
       m.reach, m.parry, m.acc, m.range_half, m.range_max, m.rof,
       m.shots, m.recoil, m.attack_modifier, m.notes
FROM weapon_modes m
LEFT JOIN skills s ON m.skill_id = s.skill_id
LEFT JOIN damage_types dt ON m.damage_type_id = dt.damage_type_id
WHERE m.weapon_id = ?
ORDER BY m.mode_id ASC
"""


def fetch_weapon_modes(
    connection: sqlite3.Connection, weapon_id: int
) -> List[Dict[str, Any]]:
    """Returns all modes of a weapon with display labels applied."""
    rows = connection.execute(WEAPON_MODE_QUERY, (weapon_id,)).fetchall()
    return [
        weapon_mode_display({key: row[key] for key in row.keys()})
        for row in rows
    ]
