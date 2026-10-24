import tempfile
import unittest
from pathlib import Path

from api.resources import RELATIONS
from app import create_app
from database.connection import (
    get_database_path,
    initialize_database,
    set_database_path,
)


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.original_path = get_database_path()
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "gurps.db"
        set_database_path(self.database_path)
        initialize_database(self.database_path)
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        set_database_path(self.original_path)
        self.temporary.cleanup()

    def create(self, url, payload):
        response = self.client.post(url, json=payload)
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def test_schema_exposes_new_columns(self):
        response = self.client.get("/api/schemas")
        self.assertEqual(response.status_code, 200)
        schemas = response.get_json()

        weapon_columns = {
            column["name"]
            for column in schemas["resources"]["weapons"]["columns"]
        }
        self.assertIn("key", weapon_columns)
        self.assertIn("is_unarmed", weapon_columns)

        mode_columns = {
            column["name"]
            for column in schemas["resources"]["weapon-modes"]["columns"]
        }
        self.assertIn("weapon_id", mode_columns)
        self.assertIn("skill_id", mode_columns)
        self.assertIn("attack_kind", mode_columns)
        self.assertIn("damage_dice", mode_columns)
        self.assertIn("damage_type_id", mode_columns)
        self.assertIn("armor_divisor", mode_columns)
        self.assertNotIn("damage_type", mode_columns)
        self.assertNotIn("skill_name", mode_columns)
        self.assertIn("damage-types", schemas["resources"])

        attack_kind = next(
            column
            for column in schemas["resources"]["weapon-modes"]["columns"]
            if column["name"] == "attack_kind"
        )
        self.assertEqual(attack_kind["option_labels"]["melee"], "Corpo a corpo")

        damage_base = next(
            column
            for column in schemas["resources"]["weapon-modes"]["columns"]
            if column["name"] == "damage_base"
        )
        self.assertEqual(damage_base["option_labels"]["swing"], "GeB")

        weapon_relation_columns = {
            column["name"]
            for column in schemas["relations"]["weapons"]["columns"]
        }
        self.assertIn("current_shots", weapon_relation_columns)
        self.assertEqual(
            schemas["relations"]["weapons"]["item_label_columns"],
            [["tl", "NT"]],
        )

        armor_columns = {
            column["name"]
            for column in schemas["relations"]["armors"]["columns"]
        }
        self.assertIn("layer_order", armor_columns)
        self.assertEqual(
            schemas["relations"]["armors"]["item_label_columns"],
            [["tl", "NT"], ["dr", "RD"]],
        )

    def test_character_additional_basic_speed_accepts_float(self):
        schemas = self.client.get("/api/schemas").get_json()
        speed_column = next(
            column
            for column in schemas["resources"]["characters"]["columns"]
            if column["name"] == "additional_basic_speed"
        )
        self.assertEqual(speed_column["type"], "float")

        character = self.create(
            "/api/characters",
            {
                "name": "Personagem Veloz",
                "dx": 10,
                "ht": 10,
                "additional_basic_speed": 0.75,
            },
        )
        self.assertEqual(character["additional_basic_speed"], 0.75)

        details = self.client.get(
            f"/api/characters/{character['character_id']}/details"
        ).get_json()
        self.assertEqual(details["character"]["additional_basic_speed"], 0.75)
        self.assertEqual(details["derived"]["basic_speed"], 5.75)
        self.assertEqual(details["derived"]["basic_move"], 5)
        self.assertEqual(details["points"]["secondary"]["speed"], 15)

        response = self.client.put(
            f"/api/characters/{character['character_id']}",
            json={"additional_basic_speed": 0.25},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["additional_basic_speed"], 0.25)

        details = self.client.get(
            f"/api/characters/{character['character_id']}/details"
        ).get_json()
        self.assertEqual(details["derived"]["basic_speed"], 5.25)
        self.assertEqual(details["points"]["secondary"]["speed"], 5)

    def test_weapon_modes_resolve_skill_and_damage_type(self):
        skill = self.create(
            "/api/skills",
            {
                "name": "Perícia de Teste",
                "attribute": "DX",
                "difficulty_id": 1,
            },
        )
        weapon = self.create(
            "/api/weapons",
            {"name": "Arma de Teste", "key": "test_weapon"},
        )
        mode = self.create(
            f"/api/weapons/{weapon['weapon_id']}/modes",
            {
                "mode_name": "Golpe",
                "skill_id": skill["skill_id"],
                "attack_kind": "melee",
                "damage_base": "thrust",
                "damage_modifier": 1,
                "attack_modifier": -2,
                "damage_type_id": 4,
                "armor_divisor": 2.0,
                "reach": "1",
                "parry": "0",
            },
        )
        self.assertEqual(mode["skill_id"], skill["skill_id"])
        self.assertEqual(mode["attack_modifier"], -2)
        self.assertEqual(mode["damage_type_id"], 4)
        self.assertEqual(mode["armor_divisor"], 2.0)

        response = self.client.get(
            f"/api/weapons/{weapon['weapon_id']}/modes"
        )
        self.assertEqual(response.status_code, 200)
        modes = response.get_json()
        self.assertEqual(modes[0]["skill_name"], "Perícia de Teste")
        self.assertEqual(modes[0]["damage_type_key"], "crushing")
        self.assertEqual(modes[0]["damage_type"], "Contusão")
        self.assertEqual(modes[0]["damage_base_label"], "GdP")
        self.assertEqual(modes[0]["attack_kind_label"], "Corpo a corpo")
        self.assertEqual(modes[0]["damage_display"], "GdP+1 Contusão (2)")
        self.assertEqual(modes[0]["attack_modifier"], -2)

        response = self.client.put(
            f"/api/weapon-modes/{mode['mode_id']}",
            json={
                "damage_base": None,
                "damage_dice": 2,
                "damage_type_id": 5,
            },
        )
        self.assertEqual(response.status_code, 200)
        updated = response.get_json()
        self.assertIsNone(updated["damage_base"])
        self.assertEqual(updated["damage_dice"], 2)

        response = self.client.post(
            f"/api/weapons/{weapon['weapon_id']}/modes",
            json={
                "mode_name": "Inválido",
                "attack_kind": "melee",
                "damage_base": "swing",
                "damage_dice": 2,
                "damage_type_id": 5,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_damage_types_lookup_exposes_labels(self):
        response = self.client.get("/api/damage-types")
        self.assertEqual(response.status_code, 200)
        damage_types = response.get_json()
        self.assertEqual(len(damage_types), 13)
        crushing = next(
            item for item in damage_types if item["key"] == "crushing"
        )
        self.assertEqual(crushing["label"], "Contusão")

    def test_character_export_renders_unified_weapons(self):
        character = self.create("/api/characters", {"name": "Personagem PDF"})
        weapon = self.create(
            "/api/weapons",
            {"name": "Arma PDF", "key": "pdf_weapon"},
        )
        self.create(
            f"/api/weapons/{weapon['weapon_id']}/modes",
            {
                "mode_name": "Golpe PDF",
                "attack_kind": "melee",
                "damage_base": "swing",
                "damage_type_id": 5,
                "reach": "1",
                "parry": "0",
            },
        )
        self.create(
            f"/api/characters/{character['character_id']}/weapons",
            {"weapon_id": weapon["weapon_id"], "current_shots": 0},
        )

        response = self.client.get(
            f"/api/characters/{character['character_id']}/export"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_schema_exposes_combat_effects(self):
        response = self.client.get("/api/schemas")
        self.assertEqual(response.status_code, 200)
        schemas = response.get_json()

        self.assertIn("combat-effects", schemas["resources"])
        self.assertIn("combat-effects", schemas["relations"])

        effect_columns = {
            column["name"]: column
            for column in schemas["resources"]["combat-effects"]["columns"]
        }
        self.assertEqual(effect_columns["applies_to"]["type"], "select")
        self.assertEqual(effect_columns["target"]["type"], "select")
        applies_to_options = set(effect_columns["applies_to"]["options"])
        for applies_to in (
            "attack",
            "damage",
            "defense",
            "dodge",
            "parry",
            "extra_defense_attempts",
            "extra_defense_uses",
            "st",
            "dx",
            "iq",
            "ht",
            "max_pv",
            "max_pf",
            "will",
            "per",
            "basic_speed",
            "basic_move",
            "ht_check",
            "rd",
        ):
            self.assertIn(applies_to, applies_to_options)

    def test_combat_effect_validation(self):
        valid = self.create(
            "/api/combat-effects",
            {
                "name": "Fúria de Teste",
                "applies_to": "attack",
                "value": -2,
                "uses_per_turn": 1,
                "notes": "Teste",
            },
        )
        self.assertEqual(valid["value"], -2)
        self.assertIsNone(valid["target"])

        normalized = self.create(
            "/api/combat-effects",
            {
                "name": "Ataque com Alvo Ignorado",
                "applies_to": "attack",
                "target": "dodge",
                "value": 1,
                "uses_per_turn": 2,
            },
        )
        self.assertIsNone(normalized["target"])
        self.assertEqual(normalized["uses_per_turn"], 2)

        passive = self.create(
            "/api/combat-effects",
            {
                "name": "Força Extra de Teste",
                "applies_to": "st",
                "target": "dodge",
                "value": 2,
                "uses_per_turn": 5,
            },
        )
        self.assertIsNone(passive["target"])
        self.assertEqual(passive["uses_per_turn"], 0)

        passive_rd = self.create(
            "/api/combat-effects",
            {
                "name": "RD Passiva de Teste",
                "applies_to": "rd",
                "target": "parry",
                "value": 3,
                "uses_per_turn": 4,
            },
        )
        self.assertIsNone(passive_rd["target"])
        self.assertEqual(passive_rd["uses_per_turn"], 0)

        invalid_cases = (
            {
                "name": "Tipo Inválido",
                "applies_to": "block",
                "value": 1,
                "uses_per_turn": 0,
            },
            {
                "name": "Block como Alvo",
                "applies_to": "dodge",
                "target": "block",
                "value": 1,
                "uses_per_turn": 0,
            },
            {
                "name": "Alvo Trocado",
                "applies_to": "dodge",
                "target": "parry",
                "value": 1,
                "uses_per_turn": 0,
            },
            {
                "name": "Usos Negativos",
                "applies_to": "damage",
                "value": 1,
                "uses_per_turn": -1,
            },
            {
                "name": "",
                "applies_to": "rd",
                "value": 1,
                "uses_per_turn": 0,
            },
        )
        for payload in invalid_cases:
            response = self.client.post("/api/combat-effects", json=payload)
            self.assertEqual(response.status_code, 400, payload)

        duplicate = self.client.post(
            "/api/combat-effects",
            json={
                "name": "fúria de teste",
                "applies_to": "damage",
                "value": 1,
                "uses_per_turn": 0,
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        targetable = self.create(
            "/api/combat-effects",
            {
                "name": "Reflexos de Teste",
                "applies_to": "extra_defense_uses",
                "target": "dodge",
                "value": 1,
                "uses_per_turn": 0,
            },
        )
        self.assertEqual(targetable["target"], "dodge")

        postura = self.create(
            "/api/combat-effects",
            {
                "name": "Postura de Teste",
                "applies_to": "parry",
                "target": "parry",
                "value": 1,
                "uses_per_turn": 1,
            },
        )
        response = self.client.put(
            f"/api/combat-effects/{postura['effect_id']}",
            json={"applies_to": "attack"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()["target"])
        self.assertEqual(response.get_json()["uses_per_turn"], 1)

        response = self.client.put(
            f"/api/combat-effects/{postura['effect_id']}",
            json={"applies_to": "st"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()["target"])
        self.assertEqual(response.get_json()["uses_per_turn"], 0)

    def test_character_combat_effect_links_are_retroactive_and_cascade(self):
        character = self.create(
            "/api/characters", {"name": "Personagem com Efeito"}
        )
        character_id = character["character_id"]
        effect = self.create(
            "/api/combat-effects",
            {
                "name": "Efeito Retroativo",
                "applies_to": "damage",
                "value": 2,
                "uses_per_turn": 1,
                "notes": "Muda depois",
            },
        )
        effect_id = effect["effect_id"]

        link = self.create(
            f"/api/characters/{character_id}/combat-effects",
            {"effect_id": effect_id},
        )
        self.assertEqual(link["effect_id"], effect_id)
        self.assertEqual(link["item_label"], "Efeito Retroativo")

        duplicate = self.client.post(
            f"/api/characters/{character_id}/combat-effects",
            json={"effect_id": effect_id},
        )
        self.assertEqual(duplicate.status_code, 409)

        details = self.client.get(
            f"/api/characters/{character_id}/details"
        ).get_json()
        self.assertEqual(details["combat_effects"][0]["item_value"], 2)

        updated = self.client.put(
            f"/api/combat-effects/{effect_id}",
            json={"value": 5, "uses_per_turn": 0},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["value"], 5)

        details = self.client.get(
            f"/api/characters/{character_id}/details"
        ).get_json()
        self.assertEqual(details["combat_effects"][0]["item_value"], 5)
        self.assertEqual(details["combat_effects"][0]["item_uses_per_turn"], 0)

        response = self.client.delete(
            f"/api/characters/{character_id}/combat-effects/{effect_id}"
        )
        self.assertEqual(response.status_code, 204)

        details = self.client.get(
            f"/api/characters/{character_id}/details"
        ).get_json()
        self.assertEqual(details["combat_effects"], [])

        self.create(
            f"/api/characters/{character_id}/combat-effects",
            {"effect_id": effect_id},
        )
        response = self.client.delete(f"/api/combat-effects/{effect_id}")
        self.assertEqual(response.status_code, 204)

        details = self.client.get(
            f"/api/characters/{character_id}/details"
        ).get_json()
        self.assertEqual(details["combat_effects"], [])

    def test_passive_effects_do_not_change_sheet_base_values(self):
        character = self.create(
            "/api/characters", {"name": "Personagem com Bônus Passivo"}
        )
        character_id = character["character_id"]
        st_effect = self.create(
            "/api/combat-effects",
            {
                "name": "Força Passiva de Teste",
                "applies_to": "st",
                "value": 2,
                "uses_per_turn": 0,
            },
        )
        pv_effect = self.create(
            "/api/combat-effects",
            {
                "name": "PV Passivo de Teste",
                "applies_to": "max_pv",
                "value": 3,
                "uses_per_turn": 0,
            },
        )
        for effect in (st_effect, pv_effect):
            self.create(
                f"/api/characters/{character_id}/combat-effects",
                {"effect_id": effect["effect_id"]},
            )

        details = self.client.get(
            f"/api/characters/{character_id}/details"
        ).get_json()
        self.assertEqual(len(details["combat_effects"]), 2)
        self.assertEqual(details["character"]["st"], 10)
        self.assertEqual(details["derived"]["pv_max"], 10)
        self.assertEqual(details["points"]["base_attributes"]["st"], 0)

    def test_character_details_include_new_fields(self):
        skill = self.create(
            "/api/skills",
            {
                "name": "Tiro de Teste",
                "attribute": "DX",
                "difficulty_id": 1,
            },
        )
        character = self.create("/api/characters", {"name": "Personagem de Teste"})
        character_id = character["character_id"]

        weapon = self.create(
            "/api/weapons",
            {"name": "Arma Detalhada", "key": "detailed_weapon"},
        )
        self.create(
            f"/api/weapons/{weapon['weapon_id']}/modes",
            {
                "mode_name": "Golpe",
                "skill_id": skill["skill_id"],
                "attack_kind": "melee",
                "damage_base": "thrust",
                "damage_modifier": 0,
                "attack_modifier": 0,
                "damage_type_id": 5,
                "reach": "1",
                "parry": "0",
            },
        )
        self.create(
            f"/api/weapons/{weapon['weapon_id']}/modes",
            {
                "mode_name": "Tiro",
                "skill_id": skill["skill_id"],
                "attack_kind": "ranged",
                "damage_dice": 2,
                "damage_modifier": 1,
                "attack_modifier": 0,
                "damage_type_id": 4,
                "acc": 3,
                "range_half": 10,
                "range_max": 15,
                "rof": 1,
                "shots": "1",
                "recoil": 1,
            },
        )
        self.create(
            f"/api/characters/{character_id}/weapons",
            {
                "weapon_id": weapon["weapon_id"],
                "custom_name": "Arma de Teste",
                "current_shots": 4,
            },
        )

        material = self.create(
            "/api/armor-materials",
            {
                "name": "Material de Teste",
                "dr": 2,
                "cost_torso": 100.0,
                "weight_torso": 3.0,
            },
        )
        body_part = self.create(
            "/api/body-parts",
            {"name": "Parte de Teste", "cost_weight_factor": 1.0},
        )
        self.create(
            f"/api/characters/{character_id}/armors",
            {
                "material_id": material["material_id"],
                "body_part_id": body_part["body_part_id"],
                "layer_order": 2,
            },
        )

        response = self.client.get(f"/api/characters/{character_id}/details")
        self.assertEqual(response.status_code, 200)
        details = response.get_json()

        detailed_weapon = details["inventory"]["weapons"][0]
        self.assertEqual(detailed_weapon["current_shots"], 4)
        self.assertEqual(detailed_weapon["key"], "detailed_weapon")
        melee_mode = detailed_weapon["modes"][0]
        ranged_mode = detailed_weapon["modes"][1]
        self.assertEqual(melee_mode["skill_name"], "Tiro de Teste")
        self.assertEqual(melee_mode["damage_type"], "Corte")
        self.assertEqual(melee_mode["attack_kind_label"], "Corpo a corpo")
        self.assertEqual(ranged_mode["damage_type"], "Contusão")
        self.assertEqual(ranged_mode["attack_kind_label"], "À distância")
        self.assertEqual(ranged_mode["damage_display"], "2d+1 Contusão")
        self.assertEqual(ranged_mode["range_display"], "10/15")
        self.assertEqual(details["inventory"]["armors"][0]["layer_order"], 2)

    def test_duplicate_character_copies_all_relations(self):
        skill = self.create(
            "/api/skills",
            {
                "name": "Perícia Duplicada",
                "attribute": "DX",
                "difficulty_id": 1,
                "description": "Descrição da perícia",
            },
        )
        spell_class = self.create(
            "/api/spell-classes", {"class": "Escola Duplicada"}
        )
        spell = self.create(
            "/api/spells",
            {
                "name": "Magia Duplicada",
                "attribute": "IQ",
                "class": spell_class["spell_class_id"],
                "difficulty_id": 1,
                "cost": 2,
                "resource": "PF",
                "description": "Descrição da magia",
            },
        )
        advantage = self.create(
            "/api/advantages",
            {
                "name": "Vantagem Duplicada",
                "cost": 5,
                "description": "Descrição da vantagem",
            },
        )
        disadvantage = self.create(
            "/api/disadvantages",
            {
                "name": "Desvantagem Duplicada",
                "cost": -5,
                "description": "Descrição da desvantagem",
            },
        )
        additional_stat = self.create(
            "/api/additional-stats", {"stat": "Stat Duplicado"}
        )
        effect = self.create(
            "/api/combat-effects",
            {
                "name": "Efeito Duplicado",
                "applies_to": "damage",
                "value": 2,
                "uses_per_turn": 1,
                "notes": "Nota do efeito",
            },
        )
        item = self.create(
            "/api/items",
            {"name": "Item Duplicado", "weight": 0.5, "cost": 10.0},
        )
        weapon = self.create(
            "/api/weapons",
            {
                "name": "Arma Duplicada",
                "key": "duplicated_weapon",
                "tl": 2,
                "min_st": 9,
                "weight": 1.5,
                "cost": 200.0,
            },
        )
        self.create(
            f"/api/weapons/{weapon['weapon_id']}/modes",
            {
                "mode_name": "Golpe Duplicado",
                "skill_id": skill["skill_id"],
                "attack_kind": "melee",
                "damage_base": "thrust",
                "damage_modifier": 1,
                "attack_modifier": 0,
                "damage_type_id": 5,
                "reach": "1",
                "parry": "0",
            },
        )
        self.create(
            f"/api/weapons/{weapon['weapon_id']}/modes",
            {
                "mode_name": "Tiro Duplicado",
                "skill_id": skill["skill_id"],
                "attack_kind": "ranged",
                "damage_dice": 1,
                "damage_modifier": 0,
                "attack_modifier": 0,
                "damage_type_id": 4,
                "acc": 2,
                "range_half": 10,
                "range_max": 15,
                "rof": 1,
                "shots": "1",
                "recoil": 1,
            },
        )
        material = self.create(
            "/api/armor-materials",
            {
                "name": "Material Duplicado",
                "dr": 2,
                "is_flexible": 1,
                "cost_torso": 100.0,
                "weight_torso": 2.0,
                "don_time": 5,
                "notes": "Nota do material",
            },
        )
        body_part = self.create(
            "/api/body-parts",
            {
                "name": "Parte Duplicada",
                "cost_weight_factor": 1.0,
                "hit_location_roll": "9-11",
                "notes": "Nota da parte",
            },
        )

        original = self.create(
            "/api/characters",
            {
                "name": "Personagem Duplicado",
                "owner_id": 123,
                "is_npc": 1,
                "st": 11,
                "dx": 12,
                "iq": 13,
                "ht": 14,
                "additional_max_pv": 2,
                "additional_vont": 1,
                "additional_per": 1,
                "additional_max_pf": 3,
                "additional_basic_speed": 0.5,
                "additional_basic_move": 1,
                "energy_reserve": 5,
                "normal_diffuse_homogeneous_unded": 2,
                "money": 100,
                "current_pv": 7,
                "current_pf": 8,
                "current_er": 4,
                "current_points": 42,
            },
        )
        character_id = original["character_id"]

        self.create(
            f"/api/characters/{character_id}/skills",
            {"skill_id": skill["skill_id"], "relative_level": 2},
        )
        self.create(
            f"/api/characters/{character_id}/spells",
            {"spell_id": spell["spell_id"], "relative_level": 1},
        )
        self.create(
            f"/api/characters/{character_id}/advantages",
            {"advantage_id": advantage["advantage_id"], "notes": "Nota"},
        )
        self.create(
            f"/api/characters/{character_id}/disadvantages",
            {"disadvantage_id": disadvantage["disadvantage_id"], "notes": "Nota"},
        )
        self.create(
            f"/api/characters/{character_id}/additional-stats",
            {
                "additional_stat_id": additional_stat["id_additional_stat"],
                "value": 3,
            },
        )
        self.create(
            f"/api/characters/{character_id}/combat-effects",
            {"effect_id": effect["effect_id"]},
        )
        self.create(
            f"/api/characters/{character_id}/items",
            {"item_id": item["item_id"], "quantity": 3, "is_equipped": 1},
        )
        self.create(
            f"/api/characters/{character_id}/weapons",
            {
                "weapon_id": weapon["weapon_id"],
                "custom_name": "Arma Afiada",
                "quantity": 2,
                "is_equipped": 1,
                "current_shots": 4,
            },
        )
        self.create(
            f"/api/characters/{character_id}/armors",
            {
                "material_id": material["material_id"],
                "body_part_id": body_part["body_part_id"],
                "custom_name": "Peitoral Duplicado",
                "quantity": 2,
                "is_equipped": 1,
                "layer_order": 2,
            },
        )

        response = self.client.post(
            f"/api/characters/{character_id}/duplicate"
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        copy = response.get_json()

        self.assertNotEqual(copy["character_id"], character_id)
        self.assertEqual(copy["name"], "Personagem Duplicado (Cópia)")
        for field, value in original.items():
            if field in {"character_id", "name"}:
                continue
            self.assertEqual(copy[field], value, field)

        def without_relation_ids(rows):
            return [
                {
                    key: value
                    for key, value in row.items()
                    if not key.startswith("character_")
                }
                for row in rows
            ]

        for relation_key in RELATIONS:
            original_rows = self.client.get(
                f"/api/characters/{character_id}/{relation_key}"
            ).get_json()
            copy_rows = self.client.get(
                f"/api/characters/{copy['character_id']}/{relation_key}"
            ).get_json()
            self.assertTrue(original_rows, relation_key)
            self.assertEqual(
                without_relation_ids(copy_rows),
                without_relation_ids(original_rows),
                relation_key,
            )

        original_details = self.client.get(
            f"/api/characters/{character_id}/details"
        ).get_json()
        copy_details = self.client.get(
            f"/api/characters/{copy['character_id']}/details"
        ).get_json()
        self.assertEqual(copy_details["derived"], original_details["derived"])
        self.assertEqual(copy_details["points"], original_details["points"])
        self.assertEqual(
            copy_details["inventory"]["total_weight"],
            original_details["inventory"]["total_weight"],
        )
        self.assertEqual(
            copy_details["inventory"]["total_cost"],
            original_details["inventory"]["total_cost"],
        )
        self.assertEqual(
            copy_details["inventory"]["weapons"][0]["modes"],
            original_details["inventory"]["weapons"][0]["modes"],
        )
        self.assertEqual(
            self.client.get(f"/api/characters/{character_id}").get_json(),
            original,
        )

        response = self.client.post(
            f"/api/characters/{character_id + 1000000}/duplicate"
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
