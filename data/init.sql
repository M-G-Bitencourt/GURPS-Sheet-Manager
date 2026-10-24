CREATE TABLE "additional_stats" (
    "id_additional_stat" INTEGER PRIMARY KEY AUTOINCREMENT,
    "stat" TEXT UNIQUE
);
CREATE TABLE "difficulties" (
    "difficulty_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "difficulty" TEXT NOT NULL UNIQUE
);
INSERT INTO "difficulties" ("difficulty_id", "difficulty") VALUES
    (1, 'Easy'),
    (2, 'Medium'),
    (3, 'Hard'),
    (4, 'Very Hard'),
    (5, 'Ultra Hard');
CREATE TABLE "skills" (
    "skill_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "name" TEXT,
    "attribute" TEXT,
    "difficulty_id" INTEGER,
    "description" TEXT,
    FOREIGN KEY("difficulty_id") REFERENCES "difficulties"("difficulty_id")
);
INSERT INTO "skills" ("name", "attribute", "difficulty_id", "description")
SELECT 'Briga', 'DX', 1, 'Perícia de combate desarmado.'
WHERE NOT EXISTS (SELECT 1 FROM "skills" WHERE "name" = 'Briga');
CREATE TABLE "characters" (
    "character_id" INTEGER PRIMARY KEY,
    "owner_id" INTEGER,
    "is_npc" INTEGER DEFAULT 0,
    "name" TEXT,
    "st" INTEGER DEFAULT 10,
    "dx" INTEGER DEFAULT 10,
    "iq" INTEGER DEFAULT 10,
    "ht" INTEGER DEFAULT 10,
    "additional_max_pv" INTEGER DEFAULT 0,
    "additional_vont" INTEGER DEFAULT 0,
    "additional_per" INTEGER DEFAULT 0,
    "additional_max_pf" INTEGER DEFAULT 0,
    "additional_basic_speed" INTEGER DEFAULT 0,
    "additional_basic_move" INTEGER DEFAULT 0,
    "energy_reserve" INTEGER DEFAULT 0,
    "normal_diffuse_homogeneous_unded" INTEGER DEFAULT 0,
    "money" INTEGER DEFAULT 0,
    "current_pv" INTEGER DEFAULT 0,
    "current_pf" INTEGER DEFAULT 0,
    "current_er" INTEGER DEFAULT 0,
    "current_points" INTEGER DEFAULT 0
);
CREATE TABLE "hdm" (
    "id_player" INTEGER PRIMARY KEY,
    "fate" INTEGER NOT NULL
);
CREATE TABLE "current_attacks" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "raw_damage" INTEGER,
    "dmg_type" INTEGER,
    "hit_location" INTEGER,
    "feint" INTEGER,
    "critical_damage" INTEGER
);
CREATE TABLE "items" (
    "item_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,
    "weight" REAL DEFAULT 0.0,
    "cost" REAL DEFAULT 0.0,
    "description" TEXT
);
CREATE TABLE "damage_types" (
    "damage_type_id" INTEGER PRIMARY KEY,
    "key" TEXT NOT NULL UNIQUE
);
INSERT INTO "damage_types" ("damage_type_id", "key") VALUES
    (1, 'affliction'),
    (2, 'burning'),
    (3, 'corrosion'),
    (4, 'crushing'),
    (5, 'cutting'),
    (6, 'fatigue'),
    (7, 'impaling'),
    (8, 'piercing_small'),
    (9, 'piercing'),
    (10, 'piercing_large'),
    (11, 'piercing_huge'),
    (12, 'special'),
    (13, 'toxic');
CREATE TABLE "weapons" (
    "weapon_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "key" TEXT UNIQUE,
    "name" TEXT NOT NULL,
    "tl" INTEGER NOT NULL DEFAULT 0 CHECK ("tl" >= 0),
    "min_st" INTEGER NOT NULL DEFAULT 0 CHECK ("min_st" >= 0),
    "is_two_handed" INTEGER NOT NULL DEFAULT 0
        CHECK ("is_two_handed" IN (0, 1)),
    "weight" REAL NOT NULL DEFAULT 0.0 CHECK ("weight" >= 0),
    "cost" REAL NOT NULL DEFAULT 0.0 CHECK ("cost" >= 0),
    "description" TEXT,
    "is_unarmed" INTEGER NOT NULL DEFAULT 0
        CHECK ("is_unarmed" IN (0, 1)),
    "is_fallback" INTEGER NOT NULL DEFAULT 0
        CHECK ("is_fallback" IN (0, 1))
);
CREATE TABLE "weapon_modes" (
    "mode_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "weapon_id" INTEGER NOT NULL,
    "mode_name" TEXT NOT NULL,
    "skill_id" INTEGER,
    "attack_kind" TEXT NOT NULL DEFAULT 'melee'
        CHECK ("attack_kind" IN ('melee', 'ranged')),
    "damage_base" TEXT
        CHECK ("damage_base" IN ('swing', 'thrust')),
    "damage_dice" INTEGER
        CHECK ("damage_dice" IS NULL OR "damage_dice" > 0),
    "damage_modifier" INTEGER NOT NULL DEFAULT 0,
    "damage_type_id" INTEGER NOT NULL,
    "armor_divisor" REAL NOT NULL DEFAULT 1.0
        CHECK ("armor_divisor" > 0),
    "reach" TEXT,
    "parry" TEXT,
    "acc" INTEGER,
    "range_half" INTEGER,
    "range_max" INTEGER,
    "rof" INTEGER,
    "shots" TEXT,
    "recoil" INTEGER,
    "attack_modifier" INTEGER NOT NULL DEFAULT 0,
    "notes" TEXT,
    CHECK ("damage_base" IS NULL OR "damage_dice" IS NULL),
    UNIQUE("weapon_id", "mode_name"),
    FOREIGN KEY("weapon_id") REFERENCES "weapons"("weapon_id") ON DELETE CASCADE,
    FOREIGN KEY("skill_id") REFERENCES "skills"("skill_id") ON DELETE RESTRICT,
    FOREIGN KEY("damage_type_id") REFERENCES "damage_types"("damage_type_id") ON DELETE RESTRICT
);
CREATE INDEX "idx_weapon_modes_weapon"
    ON "weapon_modes" ("weapon_id");
CREATE INDEX "idx_weapon_modes_skill"
    ON "weapon_modes" ("skill_id");
CREATE INDEX "idx_weapon_modes_damage_type"
    ON "weapon_modes" ("damage_type_id");
INSERT INTO "weapons" (
    "key", "name", "tl", "min_st", "is_two_handed", "weight", "cost",
    "description", "is_unarmed", "is_fallback"
)
SELECT 'brawling', 'Briga', 0, 0, 0, 0.0, 0.0,
       'Ataques desarmados de Briga.', 1, 0
WHERE NOT EXISTS (
    SELECT 1 FROM "weapons"
    WHERE "key" = 'brawling'
);
INSERT INTO "weapons" (
    "key", "name", "tl", "min_st", "is_two_handed", "weight", "cost",
    "description", "is_unarmed", "is_fallback"
)
SELECT 'unarmed_combat', 'Combate Desarmado', 0, 0, 0, 0.0, 0.0,
       'Modos genéricos para personagens sem perícia desarmada específica.',
       1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM "weapons"
    WHERE "key" = 'unarmed_combat'
);
INSERT INTO "weapon_modes" (
    "weapon_id", "mode_name", "skill_id", "attack_kind",
    "damage_base", "damage_dice", "damage_modifier", "damage_type_id",
    "armor_divisor", "reach", "parry", "notes", "attack_modifier"
)
SELECT
    w."weapon_id", 'Soco',
    (SELECT "skill_id" FROM "skills" WHERE "name" = 'Briga'),
    'melee', 'thrust', NULL, -1, 4, 1.0, 'C', 'Não',
    'GURPS 4e: thr-1 cr.', 0
FROM "weapons" w
WHERE w."key" = 'brawling'
  AND NOT EXISTS (
      SELECT 1 FROM "weapon_modes" m
      WHERE m."weapon_id" = w."weapon_id"
        AND m."mode_name" = 'Soco'
  );
INSERT INTO "weapon_modes" (
    "weapon_id", "mode_name", "skill_id", "attack_kind",
    "damage_base", "damage_dice", "damage_modifier", "damage_type_id",
    "armor_divisor", "reach", "parry", "notes", "attack_modifier"
)
SELECT
    w."weapon_id", 'Chute',
    (SELECT "skill_id" FROM "skills" WHERE "name" = 'Briga'),
    'melee', 'thrust', NULL, 0, 4, 1.0, 'C,1', 'Não',
    'GURPS 4e: thr cr; -2 para acertar.', -2
FROM "weapons" w
WHERE w."key" = 'brawling'
  AND NOT EXISTS (
      SELECT 1 FROM "weapon_modes" m
      WHERE m."weapon_id" = w."weapon_id"
        AND m."mode_name" = 'Chute'
  );
INSERT INTO "weapon_modes" (
    "weapon_id", "mode_name", "skill_id", "attack_kind",
    "damage_base", "damage_dice", "damage_modifier", "damage_type_id",
    "armor_divisor", "reach", "parry", "notes", "attack_modifier"
)
SELECT
    w."weapon_id", 'Soco', NULL,
    'melee', 'thrust', NULL, -1, 4, 1.0, 'C', 'Não',
    'GURPS 4e: thr-1 cr.', 0
FROM "weapons" w
WHERE w."key" = 'unarmed_combat'
  AND NOT EXISTS (
      SELECT 1 FROM "weapon_modes" m
      WHERE m."weapon_id" = w."weapon_id"
        AND m."mode_name" = 'Soco'
  );
INSERT INTO "weapon_modes" (
    "weapon_id", "mode_name", "skill_id", "attack_kind",
    "damage_base", "damage_dice", "damage_modifier", "damage_type_id",
    "armor_divisor", "reach", "parry", "notes", "attack_modifier"
)
SELECT
    w."weapon_id", 'Chute', NULL,
    'melee', 'thrust', NULL, 0, 4, 1.0, 'C,1', 'Não',
    'GURPS 4e: thr cr; -2 para acertar.', -2
FROM "weapons" w
WHERE w."key" = 'unarmed_combat'
  AND NOT EXISTS (
      SELECT 1 FROM "weapon_modes" m
      WHERE m."weapon_id" = w."weapon_id"
        AND m."mode_name" = 'Chute'
  );
CREATE TABLE "body_parts" (
    "body_part_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL UNIQUE,          -- Ex: 'Cabeça', 'Tronco', 'Braços', 'Pernas', 'Mãos', 'Pés'
    "cost_weight_factor" REAL NOT NULL,   -- Multiplicador decimal (Ex: Tronco = 1.0, Cabeça = 0.30, Braços = 0.50)
    "hit_location_roll" TEXT,             -- Ponto de Impacto nos dados (Ex: '3-5', '9-11', '8, 12')
    "notes" TEXT                          -- Observações do sistema (Ex: sub-áreas, proteções parciais)
);
CREATE TABLE "hit_locations" (
    "hit_location_id" INTEGER PRIMARY KEY,
    "name" TEXT NOT NULL,
    "penalty" INTEGER NOT NULL,
    "armor_body_part" TEXT NOT NULL,
    "notes" TEXT
);
INSERT INTO "hit_locations" ("hit_location_id", "name", "penalty", "armor_body_part") VALUES
    (0, 'Tronco', 0, 'Tronco'),
    (1, 'Órgãos Vitais', -3, 'Tórax'),
    (2, 'Crânio', -7, 'Crânio'),
    (3, 'Olho', -9, 'Crânio'),
    (4, 'Rosto', -5, 'Rosto'),
    (5, 'Pescoço', -5, 'Pescoço'),
    (6, 'Virilha', -3, 'Virilha'),
    (7, 'Braço', -2, 'Braços'),
    (8, 'Perna', -2, 'Pernas'),
    (9, 'Mão', -4, 'Mãos'),
    (10, 'Pé', -4, 'Pés');
CREATE TABLE "combat_sessions" (
    "session_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "guild_id" INTEGER,
    "channel_id" INTEGER NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'active' CHECK ("status" IN ('active', 'closed')),
    "round_number" INTEGER NOT NULL DEFAULT 1,
    "active_character_id" INTEGER,
    "panel_message_id" INTEGER,
    "created_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "closed_at" TEXT
);
CREATE UNIQUE INDEX "idx_combat_sessions_active_channel"
    ON "combat_sessions" ("channel_id")
    WHERE "status" = 'active';
CREATE TABLE "pending_attacks" (
    "attack_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "session_id" INTEGER,
    "guild_id" INTEGER,
    "channel_id" INTEGER NOT NULL,
    "message_id" INTEGER,
    "attacker_id" INTEGER NOT NULL,
    "attacker_character_id" INTEGER NOT NULL,
    "target_character_id" INTEGER NOT NULL,
    "target_owner_id" INTEGER,
    "weapon_name" TEXT NOT NULL,
    "mode_name" TEXT,
    "skill_name" TEXT,
    "mode_id" INTEGER,
    "attack_kind" TEXT NOT NULL DEFAULT 'melee'
        CHECK ("attack_kind" IN ('melee', 'ranged')),
    "damage_expression" TEXT,
    "maneuver" TEXT,
    "custom_modifier" INTEGER NOT NULL DEFAULT 0,
    "nh_base" INTEGER NOT NULL,
    "nh_effective" INTEGER NOT NULL,
    "attack_roll" INTEGER NOT NULL,
    "attack_margin" INTEGER NOT NULL,
    "raw_damage" INTEGER NOT NULL,
    "critical_damage" INTEGER NOT NULL,
    "max_defense_attempts" INTEGER NOT NULL DEFAULT 1,
    "defense_attempts" INTEGER NOT NULL DEFAULT 0,
    "rd" INTEGER NOT NULL DEFAULT 0,
    "damage_type" INTEGER NOT NULL,
    "armor_divisor" REAL NOT NULL DEFAULT 1.0
        CHECK ("armor_divisor" > 0),
    "hit_location" INTEGER NOT NULL,
    "hit_sublocation" TEXT,
    "hit_sublocation_roll" INTEGER,
    "feint" INTEGER NOT NULL DEFAULT 0,
    "is_critical" INTEGER NOT NULL DEFAULT 0,
    "modifiers_json" TEXT,
    "status" TEXT NOT NULL DEFAULT 'pending'
        CHECK ("status" IN ('pending', 'resolving', 'resolved', 'superseded', 'expired')),
    "created_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expires_at" TEXT,
    "resolved_at" TEXT,
    FOREIGN KEY("session_id") REFERENCES "combat_sessions"("session_id") ON DELETE SET NULL,
    FOREIGN KEY("mode_id") REFERENCES "weapon_modes"("mode_id") ON DELETE SET NULL
);
CREATE UNIQUE INDEX "idx_pending_attacks_one_per_channel"
    ON "pending_attacks" ("channel_id")
    WHERE "status" IN ('pending', 'resolving');
CREATE INDEX "idx_pending_attacks_target"
    ON "pending_attacks" ("target_character_id", "status");
CREATE TABLE "combat_effects" (
    "effect_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,
    "applies_to" TEXT NOT NULL,
    "target" TEXT,
    "value" INTEGER NOT NULL DEFAULT 0,
    "uses_per_turn" INTEGER NOT NULL DEFAULT 0,
    "notes" TEXT,
    "created_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE "character_combat_effects" (
    "character_id" INTEGER NOT NULL,
    "effect_id" INTEGER NOT NULL,
    "created_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY("character_id", "effect_id"),
    FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
    FOREIGN KEY("effect_id") REFERENCES "combat_effects"("effect_id") ON DELETE CASCADE
);
CREATE INDEX "idx_character_combat_effects_character"
    ON "character_combat_effects" ("character_id");
CREATE INDEX "idx_character_combat_effects_effect"
    ON "character_combat_effects" ("effect_id");
CREATE TABLE "combat_participants" (
    "session_id" INTEGER NOT NULL,
    "character_id" INTEGER NOT NULL,
    "owner_id" INTEGER,
    "is_npc" INTEGER NOT NULL DEFAULT 0,
    "initiative" REAL NOT NULL DEFAULT 0,
    "defense_uses_json" TEXT NOT NULL DEFAULT '{}',
    "effect_uses_json" TEXT NOT NULL DEFAULT '{}',
    "created_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY("session_id", "character_id"),
    FOREIGN KEY("session_id") REFERENCES "combat_sessions"("session_id") ON DELETE CASCADE,
    FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE
);
CREATE INDEX "idx_combat_participants_character"
    ON "combat_participants" ("character_id");
CREATE TABLE "combat_log" (
    "log_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "session_id" INTEGER,
    "channel_id" INTEGER NOT NULL,
    "event_type" TEXT NOT NULL,
    "actor_character_id" INTEGER,
    "target_character_id" INTEGER,
    "value" INTEGER,
    "hp_before" INTEGER,
    "hp_after" INTEGER,
    "description" TEXT,
    "reverted" INTEGER NOT NULL DEFAULT 0,
    "created_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY("session_id") REFERENCES "combat_sessions"("session_id") ON DELETE SET NULL
);
CREATE INDEX "idx_combat_log_session"
    ON "combat_log" ("session_id", "log_id");
CREATE TABLE "guild_settings" (
    "guild_id" INTEGER PRIMARY KEY,
    "locale" TEXT NOT NULL,
    "updated_at" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE "armor_materials" (
    "material_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,                 -- Ex: 'Couro Médio', 'Cota de Malha Pesada', 'Placas Média'
    "tl" INTEGER DEFAULT 0,               -- Nível Tecnológico (NT)
    "dr" INTEGER NOT NULL,                -- Resistência a Dano (RD)
    "is_flexible" INTEGER DEFAULT 0,      -- 1 para RD flexível (*), 0 para armadura rígida
    "cost_torso" REAL NOT NULL,           -- Custo base de referência para o Tronco ($)
    "weight_torso" REAL NOT NULL,         -- Peso base de referência para o Tronco (kg)
    "don_time" INTEGER DEFAULT 30,        -- Tempo para vestir (segundos)
    "notes" TEXT                          -- Ex: '-1 RD contra dano por perfuração', 'Combustível'
);
CREATE TABLE "next_turn_conditions" (
    "character_id" INTEGER PRIMARY KEY,
    "aim" INTEGER,
    "evaluate" INTEGER,
    "shock" INTEGER,
    "feint" INTEGER,
    "no_defense" INTEGER NOT NULL DEFAULT 0,
    "defense_bonus" INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE
);
CREATE TABLE "character_additional_stats" (
    "character_additional_stat_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "character_id" INTEGER,
    "additional_stat_id" INTEGER,
    "value" INTEGER,
    UNIQUE("character_id", "additional_stat_id"),
    FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
    FOREIGN KEY("additional_stat_id") REFERENCES "additional_stats"("id_additional_stat") ON DELETE CASCADE
);
CREATE TABLE "character_spells" (
    "character_spell_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "character_id" INTEGER NOT NULL,
    "spell_id" INTEGER NOT NULL,
    "relative_level" INTEGER,
    UNIQUE("character_id", "spell_id"),
    FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
    FOREIGN KEY("spell_id") REFERENCES "spells"("spell_id") ON DELETE CASCADE
);
CREATE TABLE "character_items" (
    "character_item_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "character_id" INTEGER NOT NULL,
    "item_id" INTEGER NOT NULL,
    "quantity" INTEGER DEFAULT 1,
    "is_equipped" INTEGER DEFAULT 0,
    FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
    FOREIGN KEY("item_id") REFERENCES "items"("item_id") ON DELETE CASCADE
);
CREATE TABLE "character_weapons" (
    "character_weapon_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "character_id" INTEGER NOT NULL,
    "weapon_id" INTEGER NOT NULL,
    "custom_name" TEXT,
    "quantity" INTEGER NOT NULL DEFAULT 1 CHECK ("quantity" >= 1),
    "is_equipped" INTEGER NOT NULL DEFAULT 0
        CHECK ("is_equipped" IN (0, 1)),
    "current_shots" INTEGER NOT NULL DEFAULT 0
        CHECK ("current_shots" >= 0),
    FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
    FOREIGN KEY("weapon_id") REFERENCES "weapons"("weapon_id") ON DELETE RESTRICT
);
CREATE UNIQUE INDEX "idx_character_weapons_unique"
    ON "character_weapons" (
        "character_id",
        "weapon_id",
        COALESCE("custom_name", '')
    );
CREATE INDEX "idx_character_weapons_character"
    ON "character_weapons" ("character_id", "is_equipped");
CREATE TABLE "character_armors" (
    "character_armor_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "character_id" INTEGER NOT NULL,
    "material_id" INTEGER NOT NULL,
    "body_part_id" INTEGER NOT NULL,
    "custom_name" TEXT,                   -- Nome opcional personalizado (Ex: 'Elmo de Batalha', 'Grevas de Infantaria')
    "quantity" INTEGER DEFAULT 1,
    "is_equipped" INTEGER DEFAULT 0,
    "layer_order" INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
    FOREIGN KEY("material_id") REFERENCES "armor_materials"("material_id") ON DELETE RESTRICT,
    FOREIGN KEY("body_part_id") REFERENCES "body_parts"("body_part_id") ON DELETE RESTRICT
);
CREATE INDEX "idx_character_armors_character"
    ON "character_armors" ("character_id", "is_equipped");
CREATE TABLE "character_skills" (
	"character_skill_id"	INTEGER,
	"character_id"	INTEGER,
	"skill_id"	INTEGER,
	"relative_level"	INTEGER,
	UNIQUE("character_id","skill_id"),
	PRIMARY KEY("character_skill_id" AUTOINCREMENT),
	FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
	FOREIGN KEY("skill_id") REFERENCES "skills"("skill_id") ON DELETE CASCADE
);
CREATE TABLE "spell_classes" (
	"spell_class_id"	INTEGER NOT NULL UNIQUE,
	"class"	TEXT,
	PRIMARY KEY("spell_class_id" AUTOINCREMENT)
);
CREATE TABLE "spells" (
	"spell_id"	INTEGER,
	"name"	TEXT,
	"attribute"	TEXT,
	"class"	INTEGER,
	"difficulty_id"	INTEGER,
	"cost"	INTEGER,
	"resource"	TEXT,
	"description"	TEXT,
	PRIMARY KEY("spell_id" AUTOINCREMENT),
	FOREIGN KEY("class") REFERENCES "spell_classes"("spell_class_id"),
	FOREIGN KEY("difficulty_id") REFERENCES "difficulties"("difficulty_id")
);
CREATE TABLE "advantages" (
	"advantage_id"	INTEGER,
	"name"	TEXT NOT NULL,
	"cost"	INTEGER DEFAULT 0,
	"description"	TEXT,
	PRIMARY KEY("advantage_id" AUTOINCREMENT)
);
CREATE TABLE "disadvantages" (
	"disadvantage_id"	INTEGER,
	"name"	TEXT NOT NULL,
	"cost"	INTEGER DEFAULT 0,
	"description"	TEXT,
	PRIMARY KEY("disadvantage_id" AUTOINCREMENT)
);
CREATE TABLE "character_advantages" (
	"character_advantage_id"	INTEGER,
	"character_id"	INTEGER NOT NULL,
	"advantage_id"	INTEGER NOT NULL,
	"notes"	TEXT,
	UNIQUE("character_id","advantage_id"),
	PRIMARY KEY("character_advantage_id" AUTOINCREMENT),
	FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
	FOREIGN KEY("advantage_id") REFERENCES "advantages"("advantage_id") ON DELETE CASCADE
);
CREATE TABLE "character_disadvantages" (
	"character_disadvantage_id"	INTEGER,
	"character_id"	INTEGER NOT NULL,
	"disadvantage_id"	INTEGER NOT NULL,
	"notes"	TEXT,
	UNIQUE("character_id","disadvantage_id"),
	PRIMARY KEY("character_disadvantage_id" AUTOINCREMENT),
	FOREIGN KEY("character_id") REFERENCES "characters"("character_id") ON DELETE CASCADE,
	FOREIGN KEY("disadvantage_id") REFERENCES "disadvantages"("disadvantage_id") ON DELETE CASCADE
);

PRAGMA user_version = 13;
