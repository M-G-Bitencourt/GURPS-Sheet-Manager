"""Catalogue endpoints: items, weapons, armour and body parts."""

from flask import Blueprint, jsonify, request

from api.crud_routes import register_crud_routes
from api.generic_crud import create_row
from api.resources import DAMAGE_TYPE_LABELS
from api.weapons import fetch_weapon_modes
from database.connection import get_connection

catalog_blueprint = Blueprint("catalog", __name__, url_prefix="/api")

CATALOG_RESOURCES = (
    "items",
    "weapons",
    "weapon-modes",
    "armor-materials",
    "body-parts",
)

for _resource_key in CATALOG_RESOURCES:
    register_crud_routes(catalog_blueprint, _resource_key)


@catalog_blueprint.get("/damage-types")
def damage_types_view():
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT "damage_type_id", "key"
            FROM "damage_types"
            ORDER BY "damage_type_id" ASC
            """
        ).fetchall()
    finally:
        connection.close()

    return jsonify(
        [
            {
                "damage_type_id": row["damage_type_id"],
                "key": row["key"],
                "label": DAMAGE_TYPE_LABELS.get(row["key"], row["key"]),
            }
            for row in rows
        ]
    )


@catalog_blueprint.get("/weapons/<int:weapon_id>/modes")
def weapon_modes_view(weapon_id: int):
    connection = get_connection()
    try:
        return jsonify(fetch_weapon_modes(connection, weapon_id))
    finally:
        connection.close()


@catalog_blueprint.post("/weapons/<int:weapon_id>/modes")
def create_weapon_mode_view(weapon_id: int):
    payload = request.get_json(silent=True) or {}
    payload["weapon_id"] = weapon_id
    return jsonify(create_row("weapon-modes", payload)), 201
