import {
    EntityManager,
    buildSubnav,
    clear,
    el,
    formatNumber,
    loadLookup,
    showToast,
    truncatedText,
} from '../components.js';
import {
    combatEffectTargetLabel,
    combatEffectTargetOptions,
    combatEffectTypeLabel,
    formatCombatEffectUses,
    formatCombatEffectValue,
    isPassiveCombatEffect,
} from '../combatEffects.js';

const TRAIT_TABS = [
    { key: 'spells', label: 'Magias' },
    { key: 'skills', label: 'Perícias' },
    { key: 'advantages', label: 'Vantagens' },
    { key: 'disadvantages', label: 'Desvantagens' },
    { key: 'spell-classes', label: 'Escolas de Magia' },
    { key: 'additional-stats', label: 'Stats Adicionais' },
    { key: 'combat-effects', label: 'Efeitos de Combate' },
];

function prepareCombatEffectForm(form) {
    const appliesTo = form.elements.namedItem('applies_to');
    const target = form.elements.namedItem('target');
    const usesPerTurn = form.elements.namedItem('uses_per_turn');
    if (!appliesTo || !target || !usesPerTurn) {
        return;
    }

    const syncFields = () => {
        const previousTarget = target.value;
        const options = combatEffectTargetOptions(appliesTo.value);
        const passive = isPassiveCombatEffect(appliesTo.value);

        target.replaceChildren();
        for (const option of options) {
            target.append(el('option', {
                value: option,
                text: option === '' ? 'Genérico (NULL)' : combatEffectTargetLabel(option),
            }));
        }
        target.value = options.includes(previousTarget) ? previousTarget : '';
        target.disabled = options.length === 1;

        usesPerTurn.disabled = passive;
        if (passive) {
            usesPerTurn.value = '0';
        }
    };

    appliesTo.addEventListener('change', syncFields);
    syncFields();
}

export function initTraitsTab(schemas) {
    const mount = document.getElementById('tab-traits');
    clear(mount);

    mount.append(el('div', { class: 'page-header' }, [
        el('div', {}, [
            el('h1', { text: 'Magias e Traços' }),
            el('div', {
                class: 'page-subtitle',
                text: 'Catálogo de magias, escolas, perícias, vantagens, desvantagens, stats adicionais e efeitos de combate.',
            }),
        ]),
    ]));

    const schoolLabels = new Map();
    const difficultyLabels = new Map();

    const loadDifficulties = async () => {
        const options = await loadLookup('difficulties', 'difficulty_id', 'difficulty');
        difficultyLabels.clear();
        for (const option of options) {
            difficultyLabels.set(option.value, option.label);
        }
    };

    const TABLE_COLUMNS = {
        spells: [
            { label: 'Nome', render: (row) => row.name },
            {
                label: 'Escola',
                render: (row) => schoolLabels.get(row.class) ?? '-',
            },
            { label: 'Atributo', render: (row) => row.attribute ?? '-' },
            { label: 'Dificuldade', render: (row) => difficultyLabels.get(row.difficulty_id) ?? '-' },
            { label: 'Custo', class: 'text-right', render: (row) => row.cost ?? 0 },
            { label: 'Recurso', render: (row) => row.resource ?? '-' },
            { label: 'Descrição', render: (row) => truncatedText(row.description) },
        ],
        skills: [
            { label: 'Nome', render: (row) => row.name },
            { label: 'Atributo', render: (row) => row.attribute ?? '-' },
            { label: 'Dificuldade', render: (row) => difficultyLabels.get(row.difficulty_id) ?? '-' },
            { label: 'Descrição', render: (row) => truncatedText(row.description) },
        ],
        advantages: [
            { label: 'Nome', render: (row) => row.name },
            { label: 'Custo (pontos)', class: 'text-right', render: (row) => formatNumber(row.cost, 0) },
            { label: 'Descrição', render: (row) => truncatedText(row.description) },
        ],
        disadvantages: [
            { label: 'Nome', render: (row) => row.name },
            { label: 'Custo (pontos)', class: 'text-right', render: (row) => formatNumber(row.cost, 0) },
            { label: 'Descrição', render: (row) => truncatedText(row.description) },
        ],
        'spell-classes': [
            { label: 'Classe', render: (row) => row.class },
        ],
        'additional-stats': [
            { label: 'Stat', render: (row) => row.stat },
        ],
        'combat-effects': [
            { label: 'ID', class: 'text-right', render: (row) => row.effect_id },
            { label: 'Nome', render: (row) => row.name },
            { label: 'Tipo', render: (row) => combatEffectTypeLabel(row.applies_to) },
            {
                label: 'Alvo',
                render: (row) => (
                    combatEffectTargetOptions(row.applies_to).length === 1
                        ? '-'
                        : combatEffectTargetLabel(row.target)
                ),
            },
            {
                label: 'Valor',
                class: 'text-right',
                render: (row) => formatCombatEffectValue(row.value),
            },
            {
                label: 'Usos/Turno',
                class: 'text-right',
                render: (row) => formatCombatEffectUses(row.applies_to, row.uses_per_turn),
            },
            { label: 'Notas', render: (row) => truncatedText(row.notes) },
        ],
    };

    const panels = {};
    const managers = {};
    const subtabContainer = el('div');

    const subnav = buildSubnav(TRAIT_TABS, (key) => {
        for (const [panelKey, panel] of Object.entries(panels)) {
            panel.classList.toggle('active', panelKey === key);
        }
    });

    mount.append(subnav.element, subtabContainer);

    for (const tab of TRAIT_TABS) {
        const panel = el('section', { class: 'subtab-panel', dataset: { subtab: tab.key } });
        panels[tab.key] = panel;
        subtabContainer.append(panel);

        managers[tab.key] = new EntityManager({
            schemas,
            resourceKey: tab.key,
            mount: panel,
            columns: TABLE_COLUMNS[tab.key],
            prepare: tab.key === 'spells'
                ? async () => {
                    await loadDifficulties();
                    const options = await loadLookup('spell-classes', 'spell_class_id', 'class');
                    schoolLabels.clear();
                    for (const option of options) {
                        schoolLabels.set(option.value, option.label);
                    }
                }
                : tab.key === 'skills'
                    ? loadDifficulties
                    : null,
            prepareForm: tab.key === 'combat-effects' ? prepareCombatEffectForm : null,
        });

        if (tab.key === 'combat-effects') {
            panel.insertBefore(
                el('p', {
                    class: 'database-hint',
                    text: 'Editar um efeito altera imediatamente todos os personagens vinculados. '
                        + 'Excluir remove os vínculos. Efeitos passivos não consomem usos e só '
                        + 'alteram o combate do Dice-Master; a ficha e o admin continuam exibindo '
                        + 'os valores base. O painel do mestre lista apenas os 25 primeiros efeitos '
                        + 'em ordem alfabética; use o ID com /combat_manage_effect para catálogos maiores.',
                }),
                managers[tab.key].tableContainer,
            );
        }
    }

    const firstKey = TRAIT_TABS[0].key;
    subnav.setActive(firstKey);
    panels[firstKey].classList.add('active');

    for (const manager of Object.values(managers)) {
        manager.refresh().catch((error) => showToast(error.message, 'error'));
    }
}
