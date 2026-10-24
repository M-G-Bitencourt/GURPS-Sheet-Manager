"""Declarative registry describing every table exposed by the REST API."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from api.errors import ApiError, NotFoundError


@dataclass(frozen=True)
class Column:
    """Single editable column with presentation metadata."""

    name: str
    label: str
    type: str = "text"
    required: bool = False
    default: Any = None
    options: Tuple[str, ...] = ()
    fk_resource: Optional[str] = None
    fk_label: Optional[str] = None
    read_only: bool = False
    multiline: bool = False
    option_labels: Tuple[Tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Resource:
    """A table with its primary key and editable columns."""

    key: str
    table: str
    pk: str
    label: str
    columns: Tuple[Column, ...]
    pk_generation: str = "auto"
    search_columns: Tuple[str, ...] = ()
    order_by: Optional[str] = None
    delete_blocked_hint: Optional[str] = None
    unique_columns: Tuple[str, ...] = ()
    validator: Optional[Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]] = None


@dataclass(frozen=True)
class Relation:
    """A table linking characters to catalogue entries."""

    key: str
    table: str
    pk: str
    label: str
    item_fk: str
    item_resource: str
    columns: Tuple[Column, ...]
    item_label: str = "name"
    item_columns: Tuple[Tuple[str, str], ...] = ()
    secondary_fk: Optional[str] = None
    secondary_resource: Optional[str] = None
    secondary_label: Optional[str] = None
    item_label_columns: Tuple[Tuple[str, str], ...] = ()


ATTRIBUTE_OPTIONS = ("ST", "DX", "IQ", "HT", "Per", "Vont")
SPELL_RESOURCE_OPTIONS = ("PV", "PF", "ER")
ATTACK_KIND_OPTIONS = ("melee", "ranged")
ATTACK_KIND_LABELS = {
    "melee": "Corpo a corpo",
    "ranged": "À distância",
}
DAMAGE_BASE_OPTIONS = ("swing", "thrust")
DAMAGE_BASE_LABELS = {
    "swing": "GeB",
    "thrust": "GdP",
}
DAMAGE_TYPE_LABELS = {
    "affliction": "Aflição",
    "burning": "Queimadura",
    "corrosion": "Corrosão",
    "crushing": "Contusão",
    "cutting": "Corte",
    "fatigue": "Fadiga",
    "impaling": "Perfuração",
    "piercing_small": "Perfurante pequena",
    "piercing": "Perfurante",
    "piercing_large": "Perfurante grande",
    "piercing_huge": "Perfurante enorme",
    "special": "Especial",
    "toxic": "Tóxico",
}

COMBAT_EFFECT_APPLIES_TO = (
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
)
COMBAT_EFFECT_TARGET_RULES = {
    "dodge": (None, "dodge"),
    "parry": (None, "parry"),
    "extra_defense_uses": (None, "dodge", "parry"),
}
COMBAT_EFFECT_TARGET_OPTIONS = ("dodge", "parry")
COMBAT_EFFECT_TARGETABLE_TYPES = frozenset(COMBAT_EFFECT_TARGET_RULES)
PASSIVE_COMBAT_EFFECT_TYPES = frozenset(
    {
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
    }
)
COMBAT_EFFECT_TYPE_LABELS = {
    "attack": "Ataque",
    "damage": "Dano",
    "defense": "Defesa",
    "dodge": "Esquiva",
    "parry": "Aparar",
    "extra_defense_attempts": "Tentativas extras de defesa",
    "extra_defense_uses": "Usos extras de defesa",
    "st": "ST adicional",
    "dx": "DX adicional",
    "iq": "IQ adicional",
    "ht": "HT adicional",
    "max_pv": "PV máximo adicional",
    "max_pf": "PF máximo adicional",
    "will": "Vontade adicional",
    "per": "Percepção adicional",
    "basic_speed": "Velocidade Básica adicional",
    "basic_move": "Deslocamento Básico adicional",
    "ht_check": "Testes de HT (morte/consciência)",
    "rd": "RD adicional",
}
COMBAT_EFFECT_TARGET_LABELS = {
    None: "Genérico",
    "dodge": "Esquiva",
    "parry": "Aparar",
}


def weapon_mode_display(mode: Mapping[str, Any]) -> Dict[str, Any]:
    """Adds pt-BR display labels to a raw weapon mode row."""
    payload = {key: mode[key] for key in mode.keys()}
    damage_type_key = payload.get("damage_type_key")
    payload["damage_type"] = DAMAGE_TYPE_LABELS.get(
        damage_type_key, damage_type_key or ""
    )
    payload["damage_base_label"] = DAMAGE_BASE_LABELS.get(payload.get("damage_base"))
    payload["attack_kind_label"] = ATTACK_KIND_LABELS.get(
        payload.get("attack_kind"), payload.get("attack_kind")
    )

    base = payload["damage_base_label"]
    if not base and payload.get("damage_dice") is not None:
        base = f'{int(payload["damage_dice"])}d'

    modifier = int(payload.get("damage_modifier") or 0)
    modifier_text = f"{modifier:+d}" if modifier else ""
    type_label = payload["damage_type"]
    divisor = float(payload.get("armor_divisor") or 1.0)
    divisor_text = "" if divisor == 1 else f" ({divisor:g})"
    damage_text = f"{base or ''}{modifier_text}".strip()
    if type_label:
        damage_text = f"{damage_text} {type_label}".strip()
    payload["damage_display"] = f"{damage_text}{divisor_text}".strip() or "-"

    if payload.get("attack_kind") == "ranged":
        range_half = payload.get("range_half")
        range_max = payload.get("range_max")
        payload["range_display"] = (
            f"{range_half if range_half is not None else '-'}/"
            f"{range_max if range_max is not None else '-'}"
            if range_half is not None or range_max is not None
            else None
        )
    else:
        payload["range_display"] = None

    return payload


def validate_weapon_mode(values: Dict[str, Any]) -> Dict[str, Any]:
    """Validates mutually exclusive damage sources and bounded values."""
    damage_base = values.get("damage_base")
    damage_dice = values.get("damage_dice")

    if damage_base not in (None, *DAMAGE_BASE_OPTIONS):
        raise ApiError("O campo 'Base de Dano' contém um valor inválido.")
    if damage_dice is not None and damage_dice <= 0:
        raise ApiError("O campo 'Dados de Dano' deve ser maior que zero.")
    if damage_base and damage_dice is not None:
        raise ApiError(
            "Preencha 'Base de Dano' ou 'Dados de Dano', não ambos."
        )

    attack_kind = values.get("attack_kind")
    if attack_kind not in ATTACK_KIND_OPTIONS:
        raise ApiError("O campo 'Tipo de Ataque' contém um valor inválido.")

    armor_divisor = values.get("armor_divisor")
    if armor_divisor is not None and armor_divisor <= 0:
        raise ApiError("O campo 'Divisor de Armadura' deve ser maior que zero.")

    return {}


def validate_combat_effect(values: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the effect and returns fields the backend must normalize."""
    name = values.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ApiError("O campo 'Nome' é obrigatório.")

    applies_to = values.get("applies_to")
    if applies_to not in COMBAT_EFFECT_APPLIES_TO:
        raise ApiError("O campo 'Tipo do Efeito' contém um valor inválido.")

    value = values.get("value")
    if value is None:
        raise ApiError("O campo 'Valor' é obrigatório.")

    if applies_to in PASSIVE_COMBAT_EFFECT_TYPES:
        return {"target": None, "uses_per_turn": 0}

    uses_per_turn = values.get("uses_per_turn")
    if uses_per_turn is None:
        raise ApiError("O campo 'Usos por Turno' é obrigatório.")
    if uses_per_turn < 0:
        raise ApiError("O campo 'Usos por Turno' não pode ser negativo.")

    allowed_targets = COMBAT_EFFECT_TARGET_RULES.get(applies_to)
    if allowed_targets is None:
        return {"target": None}

    target = values.get("target")
    if target not in allowed_targets:
        allowed_text = ", ".join(
            "genérico" if item is None else f"'{item}'"
            for item in allowed_targets
        )
        raise ApiError(
            f"Para este tipo de efeito, o alvo deve ser {allowed_text}."
        )

    return {}


CHARACTER_COLUMNS = (
    Column("character_id", "ID", "int", read_only=True),
    Column("owner_id", "ID do Dono (Discord)", "int"),
    Column("is_npc", "PdM (NPC)", "bool", default=0),
    Column("name", "Nome", "text", required=True),
    Column("st", "ST", "int", default=10),
    Column("dx", "DX", "int", default=10),
    Column("iq", "IQ", "int", default=10),
    Column("ht", "HT", "int", default=10),
    Column("additional_max_pv", "PV Adicional", "int", default=0),
    Column("additional_vont", "Vont Adicional", "int", default=0),
    Column("additional_per", "Per Adicional", "int", default=0),
    Column("additional_max_pf", "PF Adicional", "int", default=0),
    Column("additional_basic_speed", "Vel. Básica Adicional", "float", default=0.0),
    Column("additional_basic_move", "Deslocamento Adicional", "int", default=0),
    Column("energy_reserve", "Reserva de Energia", "int", default=0),
    Column(
        "normal_diffuse_homogeneous_unded",
        "Difuso/Homogêneo/Morto-Vivo (0-3)",
        "int",
        default=0,
    ),
    Column("money", "Dinheiro ($)", "int", default=0),
    Column("current_pv", "PV Atuais", "int", default=0),
    Column("current_pf", "PF Atuais", "int", default=0),
    Column("current_er", "RE Atuais", "int", default=0),
    Column("current_points", "Pontos Atuais", "int", default=0),
)


RESOURCES = {
    "characters": Resource(
        key="characters",
        table="characters",
        pk="character_id",
        label="Personagens",
        columns=CHARACTER_COLUMNS,
        pk_generation="max_plus_one",
        search_columns=("name",),
        order_by="name COLLATE NOCASE ASC",
    ),
    "items": Resource(
        key="items",
        table="items",
        pk="item_id",
        label="Itens",
        columns=(
            Column("name", "Nome", "text", required=True),
            Column("weight", "Peso (kg)", "float", default=0.0),
            Column("cost", "Custo ($)", "float", default=0.0),
            Column("description", "Descrição", "text", multiline=True),
        ),
        search_columns=("name",),
        order_by="name COLLATE NOCASE ASC",
        unique_columns=("name",),
    ),
    "damage-types": Resource(
        key="damage-types",
        table="damage_types",
        pk="damage_type_id",
        label="Tipos de Dano",
        columns=(Column("key", "Chave", "text", required=True),),
        search_columns=("key",),
        order_by="damage_type_id ASC",
        unique_columns=("key",),
    ),
    "weapons": Resource(
        key="weapons",
        table="weapons",
        pk="weapon_id",
        label="Armas",
        columns=(
            Column("key", "Chave", "text"),
            Column("name", "Nome", "text", required=True),
            Column("tl", "NT", "int", default=0),
            Column("min_st", "ST Mínimo", "int", default=0),
            Column("is_two_handed", "Duas Mãos", "bool", default=0),
            Column("weight", "Peso (kg)", "float", default=0.0),
            Column("cost", "Custo ($)", "float", default=0.0),
            Column("description", "Descrição", "text", multiline=True),
            Column("is_unarmed", "Desarmado", "bool", default=0),
            Column("is_fallback", "Fallback", "bool", default=0),
        ),
        search_columns=("name", "key"),
        order_by="name COLLATE NOCASE ASC",
        delete_blocked_hint="Existem personagens vinculados a esta arma.",
        unique_columns=("name",),
    ),
    "weapon-modes": Resource(
        key="weapon-modes",
        table="weapon_modes",
        pk="mode_id",
        label="Modos de Ataque",
        columns=(
            Column(
                "weapon_id",
                "Arma",
                "fk",
                required=True,
                fk_resource="weapons",
                fk_label="name",
            ),
            Column("mode_name", "Modo", "text", required=True),
            Column(
                "skill_id",
                "Perícia",
                "fk",
                fk_resource="skills",
                fk_label="name",
            ),
            Column(
                "attack_kind",
                "Tipo de Ataque",
                "select",
                default="melee",
                options=ATTACK_KIND_OPTIONS,
                option_labels=tuple(ATTACK_KIND_LABELS.items()),
            ),
            Column(
                "damage_base",
                "Base de Dano",
                "select",
                options=DAMAGE_BASE_OPTIONS,
                option_labels=tuple(DAMAGE_BASE_LABELS.items()),
            ),
            Column("damage_dice", "Dados de Dano", "int"),
            Column("damage_modifier", "Modificador de Dano", "int", default=0),
            Column(
                "damage_type_id",
                "Tipo de Dano",
                "fk",
                required=True,
                fk_resource="damage-types",
                fk_label="label",
            ),
            Column("armor_divisor", "Divisor de Armadura", "float", default=1.0),
            Column("reach", "Alcance", "text"),
            Column("parry", "Aparar", "text"),
            Column("acc", "Precisão (Acc)", "int"),
            Column("range_half", "Alcance 1/2D", "int"),
            Column("range_max", "Alcance Máximo", "int"),
            Column("rof", "Cadência (RoF)", "int"),
            Column("shots", "Tiros/Carga", "text"),
            Column("recoil", "Recuo (Rcl)", "int"),
            Column("attack_modifier", "Modificador de Ataque", "int", default=0),
            Column("notes", "Notas", "text", multiline=True),
        ),
        search_columns=("mode_name",),
        order_by="mode_id ASC",
        validator=validate_weapon_mode,
    ),
    "armor-materials": Resource(
        key="armor-materials",
        table="armor_materials",
        pk="material_id",
        label="Materiais de Armadura",
        columns=(
            Column("name", "Nome", "text", required=True),
            Column("tl", "NT", "int", default=0),
            Column("dr", "RD", "int", required=True),
            Column("is_flexible", "Flexível", "bool", default=0),
            Column("cost_torso", "Custo (Tronco $)", "float", required=True),
            Column("weight_torso", "Peso (Tronco kg)", "float", required=True),
            Column("don_time", "Tempo para Vestir (s)", "int", default=30),
            Column("notes", "Notas", "text", multiline=True),
        ),
        search_columns=("name",),
        order_by="name COLLATE NOCASE ASC",
        delete_blocked_hint="Existem personagens usando este material de armadura.",
        unique_columns=("name",),
    ),
    "body-parts": Resource(
        key="body-parts",
        table="body_parts",
        pk="body_part_id",
        label="Partes do Corpo",
        columns=(
            Column("name", "Nome", "text", required=True),
            Column("cost_weight_factor", "Fator Peso/Custo", "float", required=True),
            Column("hit_location_roll", "Ponto de Impacto", "text"),
            Column("notes", "Notas", "text", multiline=True),
        ),
        search_columns=("name",),
        order_by="name COLLATE NOCASE ASC",
        delete_blocked_hint="Existem personagens com armaduras vinculadas a esta parte do corpo.",
    ),
    "skills": Resource(
        key="skills",
        table="skills",
        pk="skill_id",
        label="Perícias",
        columns=(
            Column("name", "Nome", "text", required=True),
            Column("attribute", "Atributo", "enum", options=ATTRIBUTE_OPTIONS),
            Column(
                "difficulty_id",
                "Dificuldade",
                "fk",
                fk_resource="difficulties",
                fk_label="difficulty",
            ),
            Column("description", "Descrição", "text", multiline=True),
        ),
        search_columns=("name",),
        order_by="name COLLATE NOCASE ASC",
        delete_blocked_hint="Existem modos de ataque usando esta perícia.",
        unique_columns=("name",),
    ),
    "spells": Resource(
        key="spells",
        table="spells",
        pk="spell_id",
        label="Magias",
        columns=(
            Column("name", "Nome", "text", required=True),
            Column("attribute", "Atributo", "enum", options=ATTRIBUTE_OPTIONS),
            Column(
                "class",
                "Escola",
                "fk",
                fk_resource="spell-classes",
                fk_label="class",
            ),
            Column(
                "difficulty_id",
                "Dificuldade",
                "fk",
                fk_resource="difficulties",
                fk_label="difficulty",
            ),
            Column("cost", "Custo", "int", default=0),
            Column("resource", "Recurso", "enum", options=SPELL_RESOURCE_OPTIONS),
            Column("description", "Descrição", "text", multiline=True),
        ),
        search_columns=("name",),
        order_by="name COLLATE NOCASE ASC",
        unique_columns=("name",),
    ),
    "difficulties": Resource(
        key="difficulties",
        table="difficulties",
        pk="difficulty_id",
        label="Dificuldades",
        columns=(Column("difficulty", "Dificuldade", "text", required=True),),
        search_columns=("difficulty",),
        order_by="difficulty_id ASC",
        delete_blocked_hint="Existem perícias ou magias usando esta dificuldade.",
    ),
    "spell-classes": Resource(
        key="spell-classes",
        table="spell_classes",
        pk="spell_class_id",
        label="Escolas de Magia",
        columns=(Column("class", "Classe", "text", required=True),),
        search_columns=("class",),
        order_by="class COLLATE NOCASE ASC",
        delete_blocked_hint="Existem magias vinculadas a esta escola.",
    ),
    "advantages": Resource(
        key="advantages",
        table="advantages",
        pk="advantage_id",
        label="Vantagens",
        columns=(
            Column("name", "Nome", "text", required=True),
            Column("cost", "Custo (pontos)", "int", default=0),
            Column("description", "Descrição", "text", multiline=True),
        ),
        search_columns=("name",),
        order_by="name COLLATE NOCASE ASC",
        unique_columns=("name",),
    ),
    "disadvantages": Resource(
        key="disadvantages",
        table="disadvantages",
        pk="disadvantage_id",
        label="Desvantagens",
        columns=(
            Column("name", "Nome", "text", required=True),
            Column("cost", "Custo (pontos)", "int", default=0),
            Column("description", "Descrição", "text", multiline=True),
        ),
        search_columns=("name",),
        order_by="name COLLATE NOCASE ASC",
        unique_columns=("name",),
    ),
    "additional-stats": Resource(
        key="additional-stats",
        table="additional_stats",
        pk="id_additional_stat",
        label="Stats Adicionais",
        columns=(Column("stat", "Stat", "text", required=True),),
        search_columns=("stat",),
        order_by="stat COLLATE NOCASE ASC",
    ),
    "combat-effects": Resource(
        key="combat-effects",
        table="combat_effects",
        pk="effect_id",
        label="Efeitos de Combate",
        columns=(
            Column("name", "Nome", "text", required=True),
            Column(
                "applies_to",
                "Tipo do Efeito",
                "select",
                required=True,
                options=COMBAT_EFFECT_APPLIES_TO,
            ),
            Column(
                "target",
                "Alvo",
                "select",
                options=COMBAT_EFFECT_TARGET_OPTIONS,
            ),
            Column("value", "Valor", "int", default=0),
            Column("uses_per_turn", "Usos por Turno (0 = ilimitado)", "int", default=0),
            Column("notes", "Notas", "text", multiline=True),
        ),
        search_columns=("name", "applies_to", "effect_id"),
        order_by="name COLLATE NOCASE ASC, effect_id ASC",
        unique_columns=("name",),
        validator=validate_combat_effect,
    ),
}


RELATIONS = {
    "skills": Relation(
        key="skills",
        table="character_skills",
        pk="character_skill_id",
        label="Perícias",
        item_fk="skill_id",
        item_resource="skills",
        columns=(Column("relative_level", "Nível Relativo", "int", default=0),),
    ),
    "spells": Relation(
        key="spells",
        table="character_spells",
        pk="character_spell_id",
        label="Magias",
        item_fk="spell_id",
        item_resource="spells",
        columns=(Column("relative_level", "Nível Relativo", "int", default=0),),
    ),
    "advantages": Relation(
        key="advantages",
        table="character_advantages",
        pk="character_advantage_id",
        label="Vantagens",
        item_fk="advantage_id",
        item_resource="advantages",
        item_columns=(("item_cost", "cost"), ("item_description", "description")),
        columns=(Column("notes", "Notas", "text", multiline=True),),
    ),
    "disadvantages": Relation(
        key="disadvantages",
        table="character_disadvantages",
        pk="character_disadvantage_id",
        label="Desvantagens",
        item_fk="disadvantage_id",
        item_resource="disadvantages",
        item_columns=(("item_cost", "cost"), ("item_description", "description")),
        columns=(Column("notes", "Notas", "text", multiline=True),),
    ),
    "additional-stats": Relation(
        key="additional-stats",
        table="character_additional_stats",
        pk="character_additional_stat_id",
        label="Stats Adicionais",
        item_fk="additional_stat_id",
        item_resource="additional-stats",
        item_label="stat",
        columns=(Column("value", "Valor", "int", default=0),),
    ),
    "combat-effects": Relation(
        key="combat-effects",
        table="character_combat_effects",
        pk="effect_id",
        label="Efeitos de Combate",
        item_fk="effect_id",
        item_resource="combat-effects",
        columns=(),
        item_columns=(
            ("item_applies_to", "applies_to"),
            ("item_target", "target"),
            ("item_value", "value"),
            ("item_uses_per_turn", "uses_per_turn"),
            ("item_notes", "notes"),
        ),
    ),
    "items": Relation(
        key="items",
        table="character_items",
        pk="character_item_id",
        label="Itens",
        item_fk="item_id",
        item_resource="items",
        columns=(
            Column("quantity", "Quantidade", "int", default=1),
            Column("is_equipped", "Equipado", "bool", default=0),
        ),
    ),
    "weapons": Relation(
        key="weapons",
        table="character_weapons",
        pk="character_weapon_id",
        label="Armas",
        item_fk="weapon_id",
        item_resource="weapons",
        columns=(
            Column("custom_name", "Nome Personalizado", "text"),
            Column("quantity", "Quantidade", "int", default=1),
            Column("is_equipped", "Equipado", "bool", default=0),
            Column("current_shots", "Tiros Atuais", "int", default=0),
        ),
        item_label_columns=(("tl", "NT"),),
    ),
    "armors": Relation(
        key="armors",
        table="character_armors",
        pk="character_armor_id",
        label="Armaduras",
        item_fk="material_id",
        item_resource="armor-materials",
        columns=(
            Column("custom_name", "Nome Personalizado", "text"),
            Column("quantity", "Quantidade", "int", default=1),
            Column("is_equipped", "Equipado", "bool", default=0),
            Column("layer_order", "Camada", "int", default=0),
        ),
        item_label_columns=(("tl", "NT"), ("dr", "RD")),
        secondary_fk="body_part_id",
        secondary_resource="body-parts",
        secondary_label="Parte do Corpo",
    ),
}


def get_resource(resource_key: str) -> Resource:
    """Resolves a resource by key or raises a 404 domain error."""
    resource = RESOURCES.get(resource_key)
    if resource is None:
        raise NotFoundError(f"Recurso desconhecido: '{resource_key}'.")
    return resource


def get_relation(relation_key: str) -> Relation:
    """Resolves a character relation by key or raises a 404 domain error."""
    relation = RELATIONS.get(relation_key)
    if relation is None:
        raise NotFoundError(f"Relação desconhecida: '{relation_key}'.")
    return relation


def find_column(resource: Resource, column_name: str) -> Optional[Column]:
    """Returns the column metadata for the given column name, if declared."""
    for column in resource.columns:
        if column.name == column_name:
            return column
    return None
