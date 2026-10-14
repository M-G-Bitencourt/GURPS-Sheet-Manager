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

const TRAIT_TABS = [
    { key: 'spells', label: 'Magias' },
    { key: 'skills', label: 'Perícias' },
    { key: 'advantages', label: 'Vantagens' },
    { key: 'disadvantages', label: 'Desvantagens' },
    { key: 'spell-classes', label: 'Escolas de Magia' },
    { key: 'additional-stats', label: 'Stats Adicionais' },
];

export function initTraitsTab(schemas) {
    const mount = document.getElementById('tab-traits');
    clear(mount);

    mount.append(el('div', { class: 'page-header' }, [
        el('div', {}, [
            el('h1', { text: 'Magias e Traços' }),
            el('div', {
                class: 'page-subtitle',
                text: 'Catálogo de magias, escolas, perícias, vantagens, desvantagens e stats adicionais.',
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
        });
    }

    const firstKey = TRAIT_TABS[0].key;
    subnav.setActive(firstKey);
    panels[firstKey].classList.add('active');

    for (const manager of Object.values(managers)) {
        manager.refresh().catch((error) => showToast(error.message, 'error'));
    }
}
