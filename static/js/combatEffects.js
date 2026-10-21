export const PASSIVE_COMBAT_EFFECT_TYPES = new Set([
    'st',
    'dx',
    'iq',
    'ht',
    'max_pv',
    'max_pf',
    'will',
    'per',
    'basic_speed',
    'basic_move',
    'ht_check',
    'rd',
]);

export const COMBAT_EFFECT_TYPE_LABELS = {
    attack: 'Ataque',
    damage: 'Dano',
    defense: 'Defesa',
    dodge: 'Esquiva',
    parry: 'Aparar',
    extra_defense_attempts: 'Tentativas extras de defesa',
    extra_defense_uses: 'Usos extras de defesa',
    st: 'ST adicional',
    dx: 'DX adicional',
    iq: 'IQ adicional',
    ht: 'HT adicional',
    max_pv: 'PV máximo adicional',
    max_pf: 'PF máximo adicional',
    will: 'Vontade adicional',
    per: 'Percepção adicional',
    basic_speed: 'Velocidade Básica adicional',
    basic_move: 'Deslocamento Básico adicional',
    ht_check: 'Testes de HT (morte/consciência)',
    rd: 'RD adicional',
};

export const COMBAT_EFFECT_TARGET_LABELS = {
    dodge: 'Esquiva',
    parry: 'Aparar',
};

const TARGET_OPTIONS_BY_TYPE = {
    dodge: ['', 'dodge'],
    parry: ['', 'parry'],
    extra_defense_uses: ['', 'dodge', 'parry'],
};

export function isPassiveCombatEffect(appliesTo) {
    return PASSIVE_COMBAT_EFFECT_TYPES.has(appliesTo);
}

export function combatEffectTargetOptions(appliesTo) {
    return TARGET_OPTIONS_BY_TYPE[appliesTo] ?? [''];
}

export function combatEffectTypeLabel(appliesTo) {
    return COMBAT_EFFECT_TYPE_LABELS[appliesTo] ?? appliesTo ?? '-';
}

export function combatEffectTargetLabel(target) {
    if (!target) {
        return 'Genérico';
    }
    return COMBAT_EFFECT_TARGET_LABELS[target] ?? target;
}

export function formatCombatEffectValue(value) {
    const number = Number(value ?? 0);
    return number > 0 ? `+${number}` : String(number);
}

export function formatCombatEffectUses(appliesTo, value) {
    if (isPassiveCombatEffect(appliesTo)) {
        return 'Passivo';
    }
    const number = Number(value ?? 0);
    return number > 0 ? String(number) : 'Ilimitado';
}
