import tempfile
import unittest
from pathlib import Path

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

        mode_columns = {
            column["name"]
            for column in schemas["resources"]["melee-weapon-modes"]["columns"]
        }
        self.assertIn("skill_id", mode_columns)
        self.assertIn("attack_modifier", mode_columns)
        self.assertNotIn("skill_name", mode_columns)

        ranged_columns = {
            column["name"]
            for column in schemas["resources"]["ranged-weapons"]["columns"]
        }
        self.assertIn("skill_id", ranged_columns)

        armor_columns = {
            column["name"]
            for column in schemas["relations"]["armors"]["columns"]
        }
        self.assertIn("layer_order", armor_columns)

    def test_melee_modes_resolve_skill_name(self):
        skill = self.create(
            "/api/skills",
            {
                "name": "Perícia de Teste",
                "attribute": "DX",
                "difficulty_id": 1,
            },
        )
        weapon = self.create("/api/melee-weapons", {"name": "Arma de Teste"})
        mode = self.create(
            f"/api/melee-weapons/{weapon['melee_weapon_id']}/modes",
            {
                "mode_name": "Golpe",
                "skill_id": skill["skill_id"],
                "damage_base": "GdP",
                "damage_modifier": 1,
                "attack_modifier": -2,
                "damage_type": "contusão",
                "reach": "1",
                "parry": "0",
            },
        )
        self.assertEqual(mode["skill_id"], skill["skill_id"])
        self.assertEqual(mode["attack_modifier"], -2)

        response = self.client.get(
            f"/api/melee-weapons/{weapon['melee_weapon_id']}/modes"
        )
        self.assertEqual(response.status_code, 200)
        modes = response.get_json()
        self.assertEqual(modes[0]["skill_name"], "Perícia de Teste")
        self.assertEqual(modes[0]["attack_modifier"], -2)

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

        melee = self.create("/api/melee-weapons", {"name": "Arma Detalhada"})
        self.create(
            f"/api/melee-weapons/{melee['melee_weapon_id']}/modes",
            {
                "mode_name": "Golpe",
                "skill_id": skill["skill_id"],
                "damage_base": "GdP",
                "damage_modifier": 0,
                "attack_modifier": 0,
                "damage_type": "corte",
                "reach": "1",
                "parry": "0",
            },
        )
        self.create(
            f"/api/characters/{character_id}/melee-weapons",
            {"melee_weapon_id": melee["melee_weapon_id"]},
        )

        ranged = self.create(
            "/api/ranged-weapons",
            {"name": "Arma à Distância de Teste", "skill_id": skill["skill_id"]},
        )
        self.create(
            f"/api/characters/{character_id}/ranged-weapons",
            {"ranged_weapon_id": ranged["ranged_weapon_id"]},
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

        self.assertEqual(
            details["inventory"]["melee_weapons"][0]["modes"][0]["skill_name"],
            "Tiro de Teste",
        )
        self.assertEqual(
            details["inventory"]["ranged_weapons"][0]["skill_name"],
            "Tiro de Teste",
        )
        self.assertEqual(details["inventory"]["armors"][0]["layer_order"], 2)


if __name__ == "__main__":
    unittest.main()
