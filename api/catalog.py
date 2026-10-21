"""Catalogue endpoints: items, weapons, armour and body parts."""

from flask import Blueprint, jsonify, request

from api.crud_routes import register_crud_routes
from api.generic_crud import create_row
from database.connection import get_connection

catalog_blueprint = Blueprint("catalog", __name__, url_prefix="/api")

CATALOG_RESOURCES = (
    "items",
    "melee-weapons",
    "melee-weapon-modes",
    "ranged-weapons",
    "armor-materials",
    "body-parts",
)

for _resource_key in CATALOG_RESOURCES:
    register_crud_routes(catalog_blueprint, _resource_key)


def list_weapon_modes(melee_weapon_id: int):
    """Lists attack modes belonging to a single melee weapon."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT m.mode_id, m.melee_weapon_id, m.mode_name, m.skill_id,
                   s.name AS skill_name, m.damage_base, m.damage_modifier,
                   m.attack_modifier, m.damage_type, m.reach, m.parry, m.notes
            FROM melee_weapon_modes m
            LEFT JOIN skills s ON m.skill_id = s.skill_id
            WHERE m.melee_weapon_id = ?
            ORDER BY m.mode_id ASC
            """,
            (melee_weapon_id,),
        ).fetchall()
    finally:
        connection.close()
    return [{key: row[key] for key in row.keys()} for row in rows]


@catalog_blueprint.get("/melee-weapons/<int:melee_weapon_id>/modes")
def melee_weapon_modes_view(melee_weapon_id: int):
    return jsonify(list_weapon_modes(melee_weapon_id))


@catalog_blueprint.post("/melee-weapons/<int:melee_weapon_id>/modes")
def create_melee_weapon_mode_view(melee_weapon_id: int):
    payload = request.get_json(silent=True) or {}
    payload["melee_weapon_id"] = melee_weapon_id
    return jsonify(create_row("melee-weapon-modes", payload)), 201
