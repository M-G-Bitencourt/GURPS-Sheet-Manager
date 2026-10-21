"""Character endpoints: CRUD, relations and aggregated sheet data."""

import math
import sqlite3
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from api.crud_routes import register_crud_routes
from api.errors import ApiError, NotFoundError
from api.generic_crud import coerce_value, get_row, translate_integrity_error
from api.resources import RELATIONS, Relation, get_relation, get_resource
from database.connection import get_connection

characters_blueprint = Blueprint("characters", __name__, url_prefix="/api")

register_crud_routes(characters_blueprint, "characters")


def _coerce_fk(value: Any, label: str) -> int:
    """Coerces a required foreign key value coming from a form."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ApiError(f"O campo '{label}' é obrigatório.")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ApiError(f"O campo '{label}' deve ser um número inteiro.")


def _relation_item_label_column(relation: Relation) -> str:
    return relation.item_label


def _relation_select(relation: Relation) -> str:
    """Builds the shared SELECT used to list relation rows with joined labels."""
    item_resource = get_resource(relation.item_resource)
    parts = [f'r."{relation.pk}"']
    if relation.item_fk != relation.pk:
        parts.append(f'r."{relation.item_fk}"')
    parts.append(f'i."{_relation_item_label_column(relation)}" AS item_label')

    for column in relation.columns:
        parts.append(f'r."{column.name}" AS "{column.name}"')

    for alias, column_name in relation.item_columns:
        parts.append(f'i."{column_name}" AS "{alias}"')

    joins = [
        f'FROM "{relation.table}" r',
        f'JOIN "{item_resource.table}" i '
        f'ON r."{relation.item_fk}" = i."{item_resource.pk}"',
    ]

    if relation.secondary_fk and relation.secondary_resource:
        secondary = get_resource(relation.secondary_resource)
        parts.append(
            f's."{secondary.pk}" AS "{relation.secondary_fk}"'
        )
        parts.append(f's."name" AS secondary_item_label')
        joins.append(
            f'LEFT JOIN "{secondary.table}" s '
            f'ON r."{relation.secondary_fk}" = s."{secondary.pk}"'
        )

    return f"SELECT {', '.join(parts)} " + " ".join(joins)


def _relation_where(relation: Relation, include_relation_id: bool = False) -> str:
    clauses = ["r.character_id = ?"]
    if include_relation_id:
        clauses.append(f'r."{relation.pk}" = ?')
    return " WHERE " + " AND ".join(clauses)


def _relation_rows(
    connection: sqlite3.Connection,
    relation: Relation,
    parameters: tuple,
) -> List[Dict[str, Any]]:
    query = _relation_select(relation) + _relation_where(
        relation, include_relation_id=len(parameters) == 2
    )
    query += f' ORDER BY i."{relation.item_label}" COLLATE NOCASE ASC'
    rows = connection.execute(query, parameters).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def list_relations(character_id: int, relation_key: str) -> List[Dict[str, Any]]:
    """Lists every relation row bound to a character with catalogue labels."""
    relation = get_relation(relation_key)
    connection = get_connection()
    try:
        return _relation_rows(connection, relation, (character_id,))
    finally:
        connection.close()


def _fetch_relation(
    connection: sqlite3.Connection, relation: Relation, character_id: int, relation_id: int
) -> Dict[str, Any]:
    rows = _relation_rows(connection, relation, (character_id, relation_id))
    if not rows:
        raise NotFoundError(
            f"{relation.label}: vínculo {relation_id} não encontrado para este personagem."
        )
    return rows[0]


def create_relation(
    character_id: int, relation_key: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Binds a catalogue entry to a character."""
    get_row("characters", character_id)
    relation = get_relation(relation_key)

    values: Dict[str, Any] = {"character_id": character_id}
    values[relation.item_fk] = _coerce_fk(payload.get(relation.item_fk), relation.label)

    if relation.secondary_fk:
        values[relation.secondary_fk] = _coerce_fk(
            payload.get(relation.secondary_fk), relation.secondary_label or "Parte do Corpo"
        )

    for column in relation.columns:
        if column.name in payload:
            values[column.name] = coerce_value(column, payload[column.name])
        elif column.required:
            raise ApiError(f"O campo '{column.label}' é obrigatório.")
        elif column.default is not None:
            values[column.name] = column.default

    column_names = list(values.keys())
    quoted = ", ".join(f'"{name}"' for name in column_names)
    placeholders = ", ".join("?" for _ in column_names)
    query = f'INSERT INTO "{relation.table}" ({quoted}) VALUES ({placeholders})'

    connection = get_connection()
    try:
        cursor = connection.execute(query, [values[name] for name in column_names])
        connection.commit()
        new_id = values.get(relation.pk, cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        resource = get_resource(relation.item_resource)
        raise translate_integrity_error(resource, error) from error
    finally:
        connection.close()

    connection = get_connection()
    try:
        return _fetch_relation(connection, relation, character_id, new_id)
    finally:
        connection.close()


def update_relation(
    character_id: int,
    relation_key: str,
    relation_id: int,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Updates the extra columns of an existing character relation."""
    relation = get_relation(relation_key)
    updates: Dict[str, Any] = {}

    for column in relation.columns:
        if column.name in payload:
            updates[column.name] = coerce_value(column, payload[column.name])

    if relation.secondary_fk and relation.secondary_fk in payload:
        updates[relation.secondary_fk] = _coerce_fk(
            payload.get(relation.secondary_fk), relation.secondary_label or "Parte do Corpo"
        )

    if not updates:
        connection = get_connection()
        try:
            return _fetch_relation(connection, relation, character_id, relation_id)
        finally:
            connection.close()

    assignments = ", ".join(f'"{name}" = ?' for name in updates)
    query = (
        f'UPDATE "{relation.table}" SET {assignments} '
        f'WHERE "{relation.pk}" = ? AND character_id = ?'
    )
    parameters = list(updates.values()) + [relation_id, character_id]

    connection = get_connection()
    try:
        cursor = connection.execute(query, parameters)
        connection.commit()
        if cursor.rowcount == 0:
            raise NotFoundError(
                f"{relation.label}: vínculo {relation_id} não encontrado para este personagem."
            )
    except sqlite3.IntegrityError as error:
        resource = get_resource(relation.item_resource)
        raise translate_integrity_error(resource, error) from error
    finally:
        connection.close()

    connection = get_connection()
    try:
        return _fetch_relation(connection, relation, character_id, relation_id)
    finally:
        connection.close()


def delete_relation(character_id: int, relation_key: str, relation_id: int) -> None:
    """Removes a character relation without touching the catalogue entry."""
    relation = get_relation(relation_key)
    query = (
        f'DELETE FROM "{relation.table}" '
        f'WHERE "{relation.pk}" = ? AND character_id = ?'
    )

    connection = get_connection()
    try:
        cursor = connection.execute(query, (relation_id, character_id))
        connection.commit()
        if cursor.rowcount == 0:
            raise NotFoundError(
                f"{relation.label}: vínculo {relation_id} não encontrado para este personagem."
            )
    finally:
        connection.close()


def _additional_stats_map(
    connection: sqlite3.Connection, character_id: int
) -> Dict[str, int]:
    rows = connection.execute(
        """
        SELECT ads.stat, cas.value
        FROM character_additional_stats cas
        JOIN additional_stats ads
            ON cas.additional_stat_id = ads.id_additional_stat
        WHERE cas.character_id = ?
        """,
        (character_id,),
    ).fetchall()
    return {str(row["stat"]).strip().upper(): int(row["value"] or 0) for row in rows}


def _resolve_attribute(
    character: Dict[str, Any],
    additional_stats: Dict[str, int],
    attribute: Optional[str],
    default_attribute: str,
) -> tuple[int, str]:
    """Maps a raw attribute label to its effective base value and display label."""
    iq = int(character["iq"] or 0)
    per = iq + int(character["additional_per"] or 0)
    vont = iq + int(character["additional_vont"] or 0)

    normalized = (attribute or default_attribute).strip().upper()

    if normalized == "ST":
        return int(character["st"] or 0), "ST"
    if normalized == "DX":
        return int(character["dx"] or 0), "DX"
    if normalized == "IQ":
        return iq, "IQ"
    if normalized == "HT":
        return int(character["ht"] or 0), "HT"
    if normalized in ("PER", "PERCEPÇÃO", "PERCEPCAO"):
        return per, "Per"
    if normalized in ("VONT", "VONTADE", "WILL"):
        return vont, "Vont"
    if normalized in additional_stats:
        return additional_stats[normalized], attribute or normalized

    if default_attribute.upper() == "IQ":
        return iq, attribute or "IQ"
    return int(character["dx"] or 0), attribute or "DX"


DIFFICULTY_BASE = {
    "easy": 0,
    "medium": -1,
    "hard": -2,
    "very hard": -3,
    "ultra hard": -4,
}


def _relative_cost(relative_level: int, difficulty: Optional[str]) -> int:
    """Point cost of a skill or spell based on its relative level and difficulty."""
    base = DIFFICULTY_BASE.get((difficulty or "").strip().lower())
    if base is None:
        return 0

    delta = relative_level - base
    if delta < 0:
        return 0
    if delta == 0:
        return 1
    if delta == 1:
        return 2
    if delta == 2:
        return 4
    return 4 + (delta - 2) * 4


def _skill_entries(
    connection: sqlite3.Connection,
    character: Dict[str, Any],
    additional_stats: Dict[str, int],
) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            cs.character_skill_id,
            s.skill_id,
            s.name,
            s.attribute,
            d.difficulty,
            s.description,
            cs.relative_level
        FROM character_skills cs
        JOIN skills s ON cs.skill_id = s.skill_id
        LEFT JOIN difficulties d ON s.difficulty_id = d.difficulty_id
        WHERE cs.character_id = ?
        ORDER BY s.name COLLATE NOCASE ASC
        """,
        (character["character_id"],),
    ).fetchall()

    entries = []
    for row in rows:
        relative_level = int(row["relative_level"] or 0)
        base_value, label = _resolve_attribute(
            character, additional_stats, row["attribute"], "DX"
        )
        entries.append(
            {
                "character_skill_id": row["character_skill_id"],
                "skill_id": row["skill_id"],
                "name": row["name"],
                "attribute": label,
                "difficulty": row["difficulty"],
                "description": row["description"],
                "relative_level": relative_level,
                "relative_display": f"{label}{relative_level:+d}",
                "nh": base_value + relative_level,
                "point_cost": _relative_cost(relative_level, row["difficulty"]),
            }
        )
    return entries


def _spell_entries(
    connection: sqlite3.Connection,
    character: Dict[str, Any],
    additional_stats: Dict[str, int],
) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            csp.character_spell_id,
            m.spell_id,
            m.name,
            m.attribute,
            d.difficulty,
            m.cost,
            m.resource,
            m.description,
            sc.class AS school,
            csp.relative_level
        FROM character_spells csp
        JOIN spells m ON csp.spell_id = m.spell_id
        LEFT JOIN spell_classes sc ON m.class = sc.spell_class_id
        LEFT JOIN difficulties d ON m.difficulty_id = d.difficulty_id
        WHERE csp.character_id = ?
        ORDER BY sc.class COLLATE NOCASE ASC, m.name COLLATE NOCASE ASC
        """,
        (character["character_id"],),
    ).fetchall()

    entries = []
    for row in rows:
        relative_level = int(row["relative_level"] or 0)
        base_value, label = _resolve_attribute(
            character, additional_stats, row["attribute"], "IQ"
        )
        entries.append(
            {
                "character_spell_id": row["character_spell_id"],
                "spell_id": row["spell_id"],
                "name": row["name"],
                "school": row["school"] or "Sem Escola",
                "attribute": label,
                "difficulty": row["difficulty"],
                "cost": row["cost"] or 0,
                "resource": (row["resource"] or "PF").strip().upper(),
                "description": row["description"],
                "relative_level": relative_level,
                "relative_display": f"{label}{relative_level:+d}",
                "nh": base_value + relative_level,
                "point_cost": _relative_cost(relative_level, row["difficulty"]),
            }
        )
    return entries


def _trait_entries(relation_key: str, character_id: int) -> List[Dict[str, Any]]:
    entries = list_relations(character_id, relation_key)
    for entry in entries:
        entry["points"] = int(entry.get("item_cost") or 0)
    return entries


def _inventory_entries(connection: sqlite3.Connection, character_id: int) -> Dict[str, Any]:
    items_rows = connection.execute(
        """
        SELECT ci.character_item_id, ci.item_id, i.name, i.weight, i.cost,
               i.description, ci.quantity, ci.is_equipped
        FROM character_items ci
        JOIN items i ON ci.item_id = i.item_id
        WHERE ci.character_id = ?
        ORDER BY i.name COLLATE NOCASE ASC
        """,
        (character_id,),
    ).fetchall()
    items = [
        {
            "character_item_id": row["character_item_id"],
            "item_id": row["item_id"],
            "name": row["name"],
            "weight": row["weight"] or 0.0,
            "cost": row["cost"] or 0.0,
            "description": row["description"],
            "quantity": row["quantity"] or 1,
            "is_equipped": row["is_equipped"] or 0,
        }
        for row in items_rows
    ]

    melee_rows = connection.execute(
        """
        SELECT cmw.character_melee_id, cmw.melee_weapon_id, w.name, w.tl,
               w.min_st, w.is_two_handed, w.weight, w.cost, w.description,
               w.is_unarmed, w.is_fallback,
               cmw.custom_name, cmw.quantity, cmw.is_equipped
        FROM character_melee_weapons cmw
        JOIN melee_weapons w ON cmw.melee_weapon_id = w.melee_weapon_id
        WHERE cmw.character_id = ?
        ORDER BY cmw.is_equipped DESC, w.name COLLATE NOCASE ASC
        """,
        (character_id,),
    ).fetchall()
    melee_weapons = []
    for row in melee_rows:
        mode_rows = connection.execute(
            """
            SELECT m.mode_id, m.mode_name, m.skill_id, s.name AS skill_name,
                   m.damage_base, m.damage_modifier, m.attack_modifier,
                   m.damage_type, m.reach, m.parry, m.notes
            FROM melee_weapon_modes m
            LEFT JOIN skills s ON m.skill_id = s.skill_id
            WHERE m.melee_weapon_id = ?
            ORDER BY m.mode_id ASC
            """,
            (row["melee_weapon_id"],),
        ).fetchall()
        melee_weapons.append(
            {
                "character_melee_id": row["character_melee_id"],
                "melee_weapon_id": row["melee_weapon_id"],
                "name": row["name"],
                "tl": row["tl"] or 0,
                "min_st": row["min_st"] or 0,
                "is_two_handed": row["is_two_handed"] or 0,
                "weight": row["weight"] or 0.0,
                "cost": row["cost"] or 0.0,
                "description": row["description"],
                "is_unarmed": row["is_unarmed"] or 0,
                "is_fallback": row["is_fallback"] or 0,
                "custom_name": row["custom_name"],
                "quantity": row["quantity"] or 1,
                "is_equipped": row["is_equipped"] or 0,
                "modes": [
                    {
                        "mode_id": mode["mode_id"],
                        "mode_name": mode["mode_name"],
                        "skill_id": mode["skill_id"],
                        "skill_name": mode["skill_name"],
                        "damage_base": mode["damage_base"],
                        "damage_modifier": mode["damage_modifier"] or 0,
                        "attack_modifier": mode["attack_modifier"] or 0,
                        "damage_type": mode["damage_type"],
                        "reach": mode["reach"],
                        "parry": mode["parry"],
                        "notes": mode["notes"],
                    }
                    for mode in mode_rows
                ],
            }
        )

    ranged_rows = connection.execute(
        """
        SELECT crw.character_ranged_id, crw.ranged_weapon_id, w.name, w.skill_id,
               s.name AS skill_name, w.damage, w.acc, w.range_half, w.range_max,
               w.rof, w.shots, w.min_st, w.recoil, w.weight, w.cost, w.description,
               crw.quantity, crw.current_shots, crw.is_equipped
        FROM character_ranged_weapons crw
        JOIN ranged_weapons w ON crw.ranged_weapon_id = w.ranged_weapon_id
        LEFT JOIN skills s ON w.skill_id = s.skill_id
        WHERE crw.character_id = ?
        ORDER BY crw.is_equipped DESC, w.name COLLATE NOCASE ASC
        """,
        (character_id,),
    ).fetchall()
    ranged_weapons = [
        {
            "character_ranged_id": row["character_ranged_id"],
            "ranged_weapon_id": row["ranged_weapon_id"],
            "name": row["name"],
            "skill_id": row["skill_id"],
            "skill_name": row["skill_name"],
            "damage": row["damage"],
            "acc": row["acc"] or 0,
            "range_half": row["range_half"],
            "range_max": row["range_max"],
            "rof": row["rof"] or 1,
            "shots": row["shots"],
            "min_st": row["min_st"] or 0,
            "recoil": row["recoil"] or 1,
            "weight": row["weight"] or 0.0,
            "cost": row["cost"] or 0.0,
            "description": row["description"],
            "quantity": row["quantity"] or 1,
            "current_shots": row["current_shots"] or 0,
            "is_equipped": row["is_equipped"] or 0,
        }
        for row in ranged_rows
    ]

    armor_rows = connection.execute(
        """
        SELECT ca.character_armor_id, ca.material_id, ca.body_part_id,
               m.name AS material_name, m.dr, m.is_flexible, m.don_time,
               m.notes, m.weight_torso, m.cost_torso, bp.name AS body_part_name,
               bp.cost_weight_factor, ca.custom_name, ca.quantity, ca.is_equipped,
               ca.layer_order
        FROM character_armors ca
        JOIN armor_materials m ON ca.material_id = m.material_id
        JOIN body_parts bp ON ca.body_part_id = bp.body_part_id
        WHERE ca.character_id = ?
        ORDER BY ca.is_equipped DESC, bp.body_part_id ASC, ca.layer_order ASC
        """,
        (character_id,),
    ).fetchall()
    armors = []
    for row in armor_rows:
        quantity = row["quantity"] or 1
        factor = row["cost_weight_factor"] or 0.0
        armors.append(
            {
                "character_armor_id": row["character_armor_id"],
                "material_id": row["material_id"],
                "body_part_id": row["body_part_id"],
                "material_name": row["material_name"],
                "body_part_name": row["body_part_name"],
                "dr": row["dr"],
                "is_flexible": row["is_flexible"] or 0,
                "don_time": row["don_time"] or 0,
                "notes": row["notes"],
                "custom_name": row["custom_name"],
                "quantity": quantity,
                "is_equipped": row["is_equipped"] or 0,
                "layer_order": row["layer_order"] or 0,
                "weight": round((row["weight_torso"] or 0.0) * factor * quantity, 3),
                "cost": round((row["cost_torso"] or 0.0) * factor * quantity, 2),
            }
        )

    total_weight = (
        sum(entry["weight"] * entry["quantity"] for entry in items)
        + sum(entry["weight"] * entry["quantity"] for entry in melee_weapons)
        + sum(entry["weight"] * entry["quantity"] for entry in ranged_weapons)
        + sum(entry["weight"] for entry in armors)
    )
    total_cost = (
        sum(entry["cost"] * entry["quantity"] for entry in items)
        + sum(entry["cost"] * entry["quantity"] for entry in melee_weapons)
        + sum(entry["cost"] * entry["quantity"] for entry in ranged_weapons)
        + sum(entry["cost"] for entry in armors)
    )

    return {
        "items": items,
        "melee_weapons": melee_weapons,
        "ranged_weapons": ranged_weapons,
        "armors": armors,
        "total_weight": round(total_weight, 3),
        "total_cost": round(total_cost, 2),
    }


def get_character_details(character_id: int) -> Dict[str, Any]:
    """Aggregates the full sheet: attributes, derived stats, traits and inventory."""
    character = get_row("characters", character_id)

    connection = get_connection()
    try:
        additional_stats = _additional_stats_map(connection, character_id)
        skills = _skill_entries(connection, character, additional_stats)
        spells = _spell_entries(connection, character, additional_stats)
        inventory = _inventory_entries(connection, character_id)
    finally:
        connection.close()

    advantages = _trait_entries("advantages", character_id)
    disadvantages = _trait_entries("disadvantages", character_id)
    additional_stat_entries = list_relations(character_id, "additional-stats")
    combat_effects = list_relations(character_id, "combat-effects")

    st = int(character["st"] or 0)
    dx = int(character["dx"] or 0)
    iq = int(character["iq"] or 0)
    ht = int(character["ht"] or 0)

    additional_per = int(character["additional_per"] or 0)
    additional_vont = int(character["additional_vont"] or 0)
    additional_pv = int(character["additional_max_pv"] or 0)
    additional_pf = int(character["additional_max_pf"] or 0)
    additional_speed = int(character["additional_basic_speed"] or 0)
    additional_move = int(character["additional_basic_move"] or 0)

    basic_speed = round((dx + ht) / 4 + additional_speed, 2)
    basic_move = math.floor(basic_speed) + additional_move

    derived = {
        "pv_max": st + additional_pv,
        "pf_max": ht + additional_pf,
        "er": int(character["energy_reserve"] or 0),
        "basic_speed": basic_speed,
        "basic_move": basic_move,
        "per": iq + additional_per,
        "vont": iq + additional_vont,
    }

    base_attributes = {
        "st": (st - 10) * 10,
        "dx": (dx - 10) * 20,
        "iq": (iq - 10) * 20,
        "ht": (ht - 10) * 10,
    }
    base_attributes["total"] = sum(base_attributes.values())

    secondary = {
        "per": additional_per * 5,
        "vont": additional_vont * 5,
        "pv": additional_pv * 2,
        "pf": additional_pf * 3,
        "speed": int((additional_speed / 0.25) * 5),
        "move": additional_move * 5,
    }
    secondary["total"] = sum(secondary.values())

    advantage_points = sum(entry["points"] for entry in advantages)
    disadvantage_points = sum(entry["points"] for entry in disadvantages)
    skill_points = sum(entry["point_cost"] for entry in skills)
    spell_points = sum(entry["point_cost"] for entry in spells)

    points = {
        "base_attributes": base_attributes,
        "secondary": secondary,
        "advantages": advantage_points,
        "disadvantages": disadvantage_points,
        "skills": skill_points,
        "spells": spell_points,
        "total": (
            base_attributes["total"]
            + secondary["total"]
            + advantage_points
            + disadvantage_points
            + skill_points
            + spell_points
        ),
    }

    return {
        "character": character,
        "derived": derived,
        "points": points,
        "additional_stats": additional_stat_entries,
        "skills": skills,
        "spells": spells,
        "advantages": advantages,
        "disadvantages": disadvantages,
        "combat_effects": combat_effects,
        "inventory": inventory,
    }


@characters_blueprint.get("/characters/<int:character_id>/details")
def character_details_view(character_id: int):
    return jsonify(get_character_details(character_id))


def _register_relation_routes(relation_key: str) -> None:
    endpoint = relation_key.replace("-", "_")

    @characters_blueprint.get(
        f"/characters/<int:character_id>/{relation_key}",
        endpoint=f"list_character_{endpoint}",
    )
    def list_view(character_id: int):
        return jsonify(list_relations(character_id, relation_key))

    @characters_blueprint.post(
        f"/characters/<int:character_id>/{relation_key}",
        endpoint=f"create_character_{endpoint}",
    )
    def create_view(character_id: int):
        payload = request.get_json(silent=True) or {}
        return jsonify(create_relation(character_id, relation_key, payload)), 201

    @characters_blueprint.put(
        f"/characters/<int:character_id>/{relation_key}/<int:relation_id>",
        endpoint=f"update_character_{endpoint}",
    )
    def update_view(character_id: int, relation_id: int):
        payload = request.get_json(silent=True) or {}
        return jsonify(
            update_relation(character_id, relation_key, relation_id, payload)
        )

    @characters_blueprint.delete(
        f"/characters/<int:character_id>/{relation_key}/<int:relation_id>",
        endpoint=f"delete_character_{endpoint}",
    )
    def delete_view(character_id: int, relation_id: int):
        delete_relation(character_id, relation_key, relation_id)
        return "", 204


for _relation_key in RELATIONS:
    _register_relation_routes(_relation_key)
