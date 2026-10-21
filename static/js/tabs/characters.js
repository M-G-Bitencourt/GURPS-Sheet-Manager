import { api } from '../api.js';
import {
    buildBadge,
    buildForm,
    buildSubnav,
    buildTable,
    clear,
    confirmAction,
    defaultsFromColumns,
    el,
    formatNumber,
    loadLookup,
    openModal,
    readFormValues,
    showToast,
    truncatedText,
} from '../components.js';
import {
    combatEffectTargetLabel,
    combatEffectTargetOptions,
    combatEffectTypeLabel,
    formatCombatEffectUses,
    formatCombatEffectValue,
} from '../combatEffects.js';

const RELATION_PANELS = [
    { key: 'skills', label: 'Perícias' },
    { key: 'spells', label: 'Magias' },
    { key: 'advantages', label: 'Vantagens' },
    { key: 'disadvantages', label: 'Desvantagens' },
    { key: 'additional-stats', label: 'Stats Adicionais' },
    { key: 'combat-effects', label: 'Efeitos de Combate' },
    { key: 'items', label: 'Itens' },
    { key: 'melee-weapons', label: 'Armas Corpo a Corpo' },
    { key: 'ranged-weapons', label: 'Armas a Distância' },
    { key: 'armors', label: 'Armaduras' },
];

const state = {
    schemas: null,
    characters: [],
    selectedId: null,
    details: null,
    activeRelation: 'skills',
    search: '',
    listContainer: null,
    detailMount: null,
};

function itemDisplayName(row) {
    if (row.custom_name) {
        return `${row.custom_name} (${row.name})`;
    }
    if (row.material_name) {
        const base = `${row.material_name} (${row.body_part_name})`;
        return row.custom_name ? `${row.custom_name} - ${base}` : base;
    }
    return row.name ?? row.item_label ?? `#${row.item_id ?? ''}`;
}

function equippedBadge(row) {
    return row.is_equipped ? buildBadge('EQUIPADO', 'badge-equipped') : '-';
}

function effectTargetDisplay(appliesTo, target) {
    return combatEffectTargetOptions(appliesTo).length === 1
        ? '-'
        : combatEffectTargetLabel(target);
}

function definitionList(entries) {
    const list = el('dl', { class: 'detail-list' });
    for (const [label, value] of entries) {
        list.append(
            el('dt', { text: label }),
            el('dd', { text: value === null || value === undefined || value === '' ? '-' : value }),
        );
    }
    return list;
}

function descriptionBlock(text, title = 'Descrição') {
    if (!text) {
        return null;
    }
    return el('div', { class: 'detail-section' }, [
        el('h3', { class: 'detail-section__title', text: title }),
        el('p', { class: 'detail-text', text }),
    ]);
}

function modesBlock(modes) {
    return el('div', { class: 'detail-section' }, [
        el('h3', { class: 'detail-section__title', text: 'Modos de Ataque' }),
        buildTable({
            columns: [
                { label: 'Modo', render: (mode) => mode.mode_name },
                { label: 'Perícia', render: (mode) => mode.skill_name ?? '-' },
                {
                    label: 'Dano',
                    render: (mode) => `${mode.damage_base}${mode.damage_modifier >= 0 ? '+' : ''}${mode.damage_modifier} ${mode.damage_type}`,
                },
                { label: 'Mod. Ataque', class: 'text-right', render: (mode) => mode.attack_modifier ?? 0 },
                { label: 'Alcance', render: (mode) => mode.reach },
                { label: 'Aparar', render: (mode) => mode.parry },
                { label: 'Notas', render: (mode) => mode.notes ?? '-' },
            ],
            rows: modes,
            emptyMessage: 'Nenhum modo de ataque cadastrado.',
        }),
    ]);
}

const RELATION_CONFIG = {
    skills: {
        data: (details) => details.skills,
        columns: [
            { label: 'Perícia', render: (row) => row.name },
            { label: 'Atributo', render: (row) => row.attribute },
            { label: 'Dificuldade', render: (row) => row.difficulty ?? '-' },
            { label: 'Nível', class: 'mono', render: (row) => row.relative_display },
            { label: 'NH', class: 'mono text-right', render: (row) => row.nh },
            { label: 'Descrição', render: (row) => truncatedText(row.description) },
        ],
        addLabel: 'Adicionar Perícia',
        detail: (row) => [
            definitionList([
                ['Perícia', row.name],
                ['Atributo', row.attribute],
                ['Dificuldade', row.difficulty],
                ['Nível', row.relative_display],
                ['NH', row.nh],
                ['Custo em Pontos', row.point_cost],
            ]),
            descriptionBlock(row.description),
        ],
    },
    spells: {
        data: (details) => details.spells,
        columns: [
            { label: 'Magia', render: (row) => row.name },
            { label: 'Escola', render: (row) => row.school },
            { label: 'Nível', class: 'mono', render: (row) => row.relative_display },
            { label: 'NH', class: 'mono text-right', render: (row) => row.nh },
            { label: 'Custo', class: 'text-right', render: (row) => row.cost },
            { label: 'Recurso', render: (row) => row.resource },
            { label: 'Descrição', render: (row) => truncatedText(row.description) },
        ],
        addLabel: 'Adicionar Magia',
        detail: (row) => [
            definitionList([
                ['Magia', row.name],
                ['Escola', row.school],
                ['Atributo', row.attribute],
                ['Dificuldade', row.difficulty],
                ['Nível', row.relative_display],
                ['NH', row.nh],
                ['Custo', row.cost],
                ['Recurso', row.resource],
                ['Custo em Pontos', row.point_cost],
            ]),
            descriptionBlock(row.description),
        ],
    },
    advantages: {
        data: (details) => details.advantages,
        columns: [
            { label: 'Vantagem', render: (row) => row.item_label },
            {
                label: 'Custo (pontos)',
                class: 'text-right',
                render: (row) => formatNumber(row.points, 0),
            },
            { label: 'Notas', render: (row) => truncatedText(row.notes) },
        ],
        addLabel: 'Adicionar Vantagem',
        detail: (row) => [
            definitionList([
                ['Vantagem', row.item_label],
                ['Custo (pontos)', row.points],
                ['Notas', row.notes],
            ]),
            descriptionBlock(row.item_description),
        ],
    },
    disadvantages: {
        data: (details) => details.disadvantages,
        columns: [
            { label: 'Desvantagem', render: (row) => row.item_label },
            {
                label: 'Custo (pontos)',
                class: 'text-right',
                render: (row) => formatNumber(row.points, 0),
            },
            { label: 'Notas', render: (row) => truncatedText(row.notes) },
        ],
        addLabel: 'Adicionar Desvantagem',
        detail: (row) => [
            definitionList([
                ['Desvantagem', row.item_label],
                ['Custo (pontos)', row.points],
                ['Notas', row.notes],
            ]),
            descriptionBlock(row.item_description),
        ],
    },
    'additional-stats': {
        data: (details) => details.additional_stats,
        columns: [
            { label: 'Stat', render: (row) => row.item_label },
            { label: 'Valor', class: 'text-right', render: (row) => row.value },
        ],
        addLabel: 'Adicionar Stat',
        detail: (row) => [
            definitionList([
                ['Stat', row.item_label],
                ['Valor', row.value],
            ]),
        ],
    },
    'combat-effects': {
        data: (details) => details.combat_effects,
        columns: [
            { label: 'Efeito', render: (row) => row.item_label },
            { label: 'Tipo', render: (row) => combatEffectTypeLabel(row.item_applies_to) },
            {
                label: 'Alvo',
                render: (row) => effectTargetDisplay(row.item_applies_to, row.item_target),
            },
            {
                label: 'Valor',
                class: 'text-right',
                render: (row) => formatCombatEffectValue(row.item_value),
            },
            {
                label: 'Usos/Turno',
                class: 'text-right',
                render: (row) => formatCombatEffectUses(row.item_applies_to, row.item_uses_per_turn),
            },
            { label: 'Notas', render: (row) => truncatedText(row.item_notes) },
        ],
        addLabel: 'Adicionar Efeito',
        detail: (row) => [
            definitionList([
                ['Efeito', row.item_label],
                ['Tipo', combatEffectTypeLabel(row.item_applies_to)],
                ['Alvo', effectTargetDisplay(row.item_applies_to, row.item_target)],
                ['Valor', formatCombatEffectValue(row.item_value)],
                ['Usos por Turno', formatCombatEffectUses(row.item_applies_to, row.item_uses_per_turn)],
                ['Notas', row.item_notes],
            ]),
        ],
    },
    items: {
        data: (details) => details.inventory.items,
        columns: [
            { label: 'Item', render: (row) => itemDisplayName(row) },
            { label: 'Quantidade', class: 'text-right', render: (row) => row.quantity },
            { label: 'Peso (kg)', class: 'text-right', render: (row) => formatNumber(row.weight) },
            {
                label: 'Custo ($)',
                class: 'text-right',
                render: (row) => formatNumber(row.cost * (row.quantity || 1)),
            },
            { label: 'Equipado', render: equippedBadge },
        ],
        addLabel: 'Adicionar Item',
        canToggleEquip: true,
        detail: (row) => [
            definitionList([
                ['Item', row.name],
                ['Quantidade', row.quantity],
                ['Peso Unitário (kg)', formatNumber(row.weight, 3)],
                ['Custo Unitário ($)', formatNumber(row.cost)],
                ['Estado', row.is_equipped ? 'EQUIPADO' : 'Guardado'],
            ]),
            descriptionBlock(row.description),
        ],
    },
    'melee-weapons': {
        data: (details) => details.inventory.melee_weapons,
        columns: [
            { label: 'Arma', render: (row) => itemDisplayName(row) },
            { label: 'ST Min.', class: 'text-right', render: (row) => row.min_st },
            { label: 'Peso (kg)', class: 'text-right', render: (row) => formatNumber(row.weight) },
            { label: 'Quantidade', class: 'text-right', render: (row) => row.quantity },
            { label: 'Equipado', render: equippedBadge },
        ],
        addLabel: 'Adicionar Arma',
        canToggleEquip: true,
        detail: (row) => [
            definitionList([
                ['Arma', row.custom_name ? `${row.custom_name} (${row.name})` : row.name],
                ['NT', row.tl],
                ['ST Mínimo', row.min_st],
                ['Empunhadura', row.is_two_handed ? 'Duas Mãos' : 'Uma Mão'],
                ['Desarmado', row.is_unarmed ? 'Sim' : 'Não'],
                ['Fallback', row.is_fallback ? 'Sim' : 'Não'],
                ['Peso (kg)', formatNumber(row.weight, 3)],
                ['Custo ($)', formatNumber(row.cost)],
                ['Quantidade', row.quantity],
                ['Estado', row.is_equipped ? 'EQUIPADO' : 'Guardado'],
            ]),
            descriptionBlock(row.description),
            modesBlock(row.modes || []),
        ],
    },
    'ranged-weapons': {
        data: (details) => details.inventory.ranged_weapons,
        columns: [
            { label: 'Arma', render: (row) => itemDisplayName(row) },
            { label: 'Dano', render: (row) => row.damage ?? '-' },
            { label: 'Tiros', render: (row) => `${row.current_shots} / ${row.shots ?? '-'}` },
            { label: 'Peso (kg)', class: 'text-right', render: (row) => formatNumber(row.weight) },
            { label: 'Equipado', render: equippedBadge },
        ],
        addLabel: 'Adicionar Arma',
        canToggleEquip: true,
        detail: (row) => [
            definitionList([
                ['Arma', row.name],
                ['Perícia', row.skill_name || '-'],
                ['Dano', row.damage],
                ['Precisão (Acc)', row.acc],
                ['Alcance 1/2D', row.range_half],
                ['Alcance Máximo', row.range_max],
                ['Cadência (RoF)', row.rof],
                ['Tiros/Carga', row.shots],
                ['Tiros Atuais', row.current_shots],
                ['ST Mínimo', row.min_st],
                ['Recuo (Rcl)', row.recoil],
                ['Peso (kg)', formatNumber(row.weight, 3)],
                ['Custo ($)', formatNumber(row.cost)],
                ['Quantidade', row.quantity],
                ['Estado', row.is_equipped ? 'EQUIPADO' : 'Guardado'],
            ]),
            descriptionBlock(row.description),
        ],
    },
    armors: {
        data: (details) => details.inventory.armors,
        columns: [
            { label: 'Peça', render: (row) => itemDisplayName(row) },
            { label: 'RD', class: 'text-right', render: (row) => row.dr },
            { label: 'Parte', render: (row) => row.body_part_name },
            { label: 'Camada', class: 'text-right', render: (row) => row.layer_order ?? 0 },
            { label: 'Peso (kg)', class: 'text-right', render: (row) => formatNumber(row.weight) },
            {
                label: 'Custo ($)',
                class: 'text-right',
                render: (row) => formatNumber(row.cost),
            },
            { label: 'Equipado', render: equippedBadge },
        ],
        addLabel: 'Adicionar Armadura',
        canToggleEquip: true,
        detail: (row) => [
            definitionList([
                ['Peça', row.custom_name || `${row.material_name} (${row.body_part_name})`],
                ['Material', row.material_name],
                ['Parte do Corpo', row.body_part_name],
                ['Resistência a Dano (RD)', row.dr],
                ['Flexível', row.is_flexible ? 'Sim' : 'Não'],
                ['Camada', row.layer_order ?? 0],
                ['Tempo para Vestir (s)', row.don_time],
                ['Peso (kg)', formatNumber(row.weight, 3)],
                ['Custo ($)', formatNumber(row.cost)],
                ['Quantidade', row.quantity],
                ['Estado', row.is_equipped ? 'EQUIPADO' : 'Guardado'],
            ]),
            descriptionBlock(row.notes, 'Notas'),
        ],
    },
};

function pointsSection(points) {
    const entries = [
        ['Vantagens', points.advantages],
        ['Desvantagens', points.disadvantages],
        ['Atributos Base', points.base_attributes.total],
        ['Características Secundárias', points.secondary.total],
        ['Perícias', points.skills],
        ['Magias', points.spells],
    ];

    const cards = entries.map(([label, value]) => el('div', { class: 'stat-card' }, [
        el('span', { class: 'stat-label', text: label }),
        el('span', { class: 'stat-value', text: formatNumber(value, 0) }),
    ]));

    cards.push(el('div', { class: 'stat-card stat-card-total' }, [
        el('span', { class: 'stat-label', text: 'Total Geral' }),
        el('span', { class: 'stat-value', text: formatNumber(points.total, 0) }),
    ]));

    return el('div', { class: 'stat-section' }, [
        el('h3', { text: 'Pontos' }),
        el('div', { class: 'stat-grid' }, cards),
    ]);
}

function openDetailModal(relationKey, row) {
    const config = RELATION_CONFIG[relationKey];
    const parts = config.detail(row).filter(Boolean);
    const title = row.name ?? row.custom_name ?? row.item_label ?? 'Detalhes';
    openModal({
        title: `Detalhes - ${title}`,
        body: el('div', {}, parts),
        wide: true,
    });
}

function statSection(title, entries) {
    return el('div', { class: 'stat-section' }, [
        el('h3', { text: title }),
        el('div', { class: 'stat-grid' }, entries.map(([label, value]) => el('div', { class: 'stat-card' }, [
            el('span', { class: 'stat-label', text: label }),
            el('span', {
                class: 'stat-value',
                text: typeof value === 'number' ? formatNumber(value, 2) : String(value ?? '-'),
            }),
        ]))),
    ]);
}

export function initCharactersTab(schemas) {
    state.schemas = schemas;

    const mount = document.getElementById('tab-characters');
    clear(mount);

    const searchInput = el('input', {
        type: 'search',
        class: 'search-input',
        placeholder: 'Buscar por nome...',
    });
    searchInput.addEventListener('input', () => {
        state.search = searchInput.value.trim().toLowerCase();
        renderCharacterList();
    });

    state.listContainer = el('div', { class: 'character-list' });
    state.detailMount = el('div', { class: 'character-detail' });

    const listPanel = el('div', { class: 'character-list-panel' }, [
        el('div', { class: 'panel-title' }, [
            el('h3', { text: 'Personagens' }),
            el('button', {
                type: 'button',
                class: 'btn btn-primary btn-small',
                text: 'Novo',
                onclick: () => openCharacterForm(null),
            }),
        ]),
        searchInput,
        state.listContainer,
    ]);

    mount.append(el('div', { class: 'characters-layout' }, [listPanel, state.detailMount]));

    loadCharacters().catch((error) => showToast(error.message, 'error'));
}

async function loadCharacters() {
    state.characters = await api.get('/api/characters');

    if (!state.characters.some((character) => character.character_id === state.selectedId)) {
        state.selectedId = state.characters.length ? state.characters[0].character_id : null;
    }

    renderCharacterList();

    if (state.selectedId !== null) {
        await loadDetails();
    } else {
        state.details = null;
        renderDetail();
    }
}

function renderCharacterList() {
    const container = state.listContainer;
    clear(container);

    const rows = state.characters.filter((character) => (
        !state.search || String(character.name ?? '').toLowerCase().includes(state.search)
    ));

    if (!rows.length) {
        container.append(el('div', { class: 'empty-state', text: 'Nenhum personagem encontrado.' }));
        return;
    }

    for (const character of rows) {
        container.append(el('button', {
            type: 'button',
            class: `character-list-item${character.character_id === state.selectedId ? ' active' : ''}`,
            onclick: () => selectCharacter(character.character_id),
        }, [
            el('span', { text: character.name ?? `Personagem ${character.character_id}` }),
            character.is_npc
                ? buildBadge('PdM', 'badge-npc')
                : el('span', { class: 'muted mono', text: `#${character.character_id}` }),
        ]));
    }
}

async function selectCharacter(characterId) {
    state.selectedId = characterId;
    renderCharacterList();
    await loadDetails();
}

async function loadDetails() {
    state.details = await api.get(`/api/characters/${state.selectedId}/details`);
    renderDetail();
}

function renderDetail() {
    const mount = state.detailMount;
    clear(mount);

    if (!state.details) {
        mount.append(el('div', { class: 'empty-state', text: 'Selecione ou crie um personagem.' }));
        return;
    }

    const details = state.details;
    const character = details.character;
    const derived = details.derived;
    const summary = state.characters.find((item) => item.character_id === character.character_id) || character;

    const header = el('div', { class: 'character-detail-header' }, [
        el('div', {}, [
            el('h1', {}, [
                character.name ?? `Personagem ${character.character_id}`,
                character.is_npc ? buildBadge('PdM', 'badge-npc') : null,
            ]),
            el('div', {
                class: 'page-subtitle',
                text: `ID ${character.character_id}${character.owner_id ? ` - Dono: ${character.owner_id}` : ''}`,
            }),
        ]),
        el('div', { class: 'character-actions' }, [
            el('button', {
                type: 'button',
                class: 'btn btn-primary',
                text: 'Editar Personagem',
                onclick: () => openCharacterForm(summary),
            }),
            el('button', {
                type: 'button',
                class: 'btn',
                text: 'Exportar Personagem',
                onclick: exportCharacter,
            }),
            el('button', {
                type: 'button',
                class: 'btn btn-danger',
                text: 'Excluir Personagem',
                onclick: deleteCharacter,
            }),
        ]),
    ]);

    const primary = statSection('Atributos Primários', [
        ['ST', character.st],
        ['DX', character.dx],
        ['IQ', character.iq],
        ['HT', character.ht],
    ]);

    const resources = statSection('Recursos', [
        ['PV Máximos', derived.pv_max],
        ['PV Atuais', character.current_pv],
        ['PF Máximos', derived.pf_max],
        ['PF Atuais', character.current_pf],
        ['Reserva de Energia', derived.er],
        ['RE Atuais', character.current_er],
        ['Dinheiro ($)', formatNumber(character.money, 0)],
        ['Pontos Atuais', character.current_points],
    ]);

    const secondary = statSection('Secundários', [
        ['Vel. Básica', derived.basic_speed],
        ['Deslocamento', derived.basic_move],
        ['Percepção', derived.per],
        ['Vontade', derived.vont],
    ]);

    const load = statSection('Carga', [
        ['Peso Total (kg)', formatNumber(details.inventory.total_weight, 3)],
    ]);

    const relationMount = el('div');
    const relationPanels = {};

    const subnav = buildSubnav(RELATION_PANELS, (key) => {
        state.activeRelation = key;
        for (const [panelKey, panel] of Object.entries(relationPanels)) {
            panel.classList.toggle('active', panelKey === key);
        }
        renderRelationPanel(key);
    });

    for (const panel of RELATION_PANELS) {
        const panelNode = el('section', { class: 'subtab-panel', dataset: { subtab: panel.key } });
        relationPanels[panel.key] = panelNode;
        relationMount.append(panelNode);
    }

    subnav.setActive(state.activeRelation);
    relationPanels[state.activeRelation].classList.add('active');

    mount.append(header, primary, resources, secondary, pointsSection(details.points), load, el('div', { class: 'panel' }, [
        el('div', { class: 'panel-title' }, [
            el('h2', { text: 'Habilidades e Inventário' }),
        ]),
        subnav.element,
        relationMount,
    ]));

    renderRelationPanel(state.activeRelation);
}

function renderRelationPanel(relationKey) {
    const config = RELATION_CONFIG[relationKey];
    const relation = state.schemas.relations[relationKey];
    const panel = state.detailMount.querySelector(`.subtab-panel[data-subtab="${relationKey}"]`);

    if (!panel) {
        return;
    }

    clear(panel);

    const addButton = el('button', {
        type: 'button',
        class: 'btn btn-primary btn-small',
        text: config.addLabel,
        onclick: () => openRelationForm(relationKey, null),
    });

    const toolbar = el('div', { class: 'toolbar' }, [
        el('span', { class: 'spacer' }),
        addButton,
    ]);

    const actions = [];
    if (relation.columns.length || relation.secondary_fk) {
        actions.push({ label: 'Editar', onClick: (row) => openRelationForm(relationKey, row) });
    }

    if (config.canToggleEquip) {
        actions.push({
            label: (row) => (row.is_equipped ? 'Desequipar' : 'Equipar'),
            onClick: async (row) => {
                try {
                    await api.put(
                        `/api/characters/${state.selectedId}/${relationKey}/${row[relation.pk]}`,
                        { is_equipped: row.is_equipped ? 0 : 1 },
                    );
                    await loadDetails();
                } catch (error) {
                    showToast(error.message, 'error');
                }
            },
        });
    }

    actions.push({
        label: 'Excluir',
        class: 'btn-danger',
        onClick: async (row) => {
            const confirmed = await confirmAction('Remover este vínculo do personagem?');
            if (!confirmed) {
                return;
            }
            try {
                await api.delete(
                    `/api/characters/${state.selectedId}/${relationKey}/${row[relation.pk]}`,
                );
                showToast('Vínculo removido.', 'success');
                await loadDetails();
            } catch (error) {
                showToast(error.message, 'error');
            }
        },
    });

    const rows = config.data(state.details);

    panel.append(
        toolbar,
        buildTable({
            columns: config.columns,
            rows,
            emptyMessage: 'Nenhum registro vinculado.',
            actions,
            onRowClick: (row) => openDetailModal(relationKey, row),
        }),
    );
}

async function openRelationForm(relationKey, row) {
    const relation = state.schemas.relations[relationKey];
    const config = RELATION_CONFIG[relationKey];

    const itemResource = state.schemas.resources[relation.item_resource];
    const itemOptions = await loadLookup(
        relation.item_resource,
        itemResource.pk,
        relation.item_label,
    );

    const lookups = { [relation.item_resource]: itemOptions };
    const columns = [];

    if (!row) {
        columns.push({
            name: relation.item_fk,
            label: relationKey === 'armors'
                ? 'Material'
                : relationKey === 'combat-effects'
                    ? 'Efeito'
                    : 'Registro',
            type: 'fk',
            required: true,
            fk_resource: relation.item_resource,
            fk_label: relation.item_label,
        });
    }

    columns.push(...relation.columns);

    if (relation.secondary_fk) {
        const secondaryResource = state.schemas.resources[relation.secondary_resource];
        lookups[relation.secondary_resource] = await loadLookup(
            relation.secondary_resource,
            secondaryResource.pk,
            'name',
        );
        columns.push({
            name: relation.secondary_fk,
            label: relation.secondary_label,
            type: 'fk',
            required: true,
            fk_resource: relation.secondary_resource,
            fk_label: 'name',
        });
    }

    const values = row || defaultsFromColumns(columns);
    const form = buildForm(columns, values, lookups);
    const errorNode = el('div', { class: 'form-error hidden' });
    form.append(errorNode);

    const cancelButton = el('button', {
        type: 'button',
        class: 'btn',
        text: 'Cancelar',
        onclick: () => controller.close(),
    });

    const saveButton = el('button', { type: 'button', class: 'btn btn-primary', text: 'Salvar' });

    const controller = openModal({
        title: row ? `Editar - ${relation.label}` : config.addLabel,
        body: form,
        footer: [cancelButton, saveButton],
        wide: true,
    });

    saveButton.addEventListener('click', async () => {
        const payload = readFormValues(form);
        try {
            if (row) {
                await api.put(
                    `/api/characters/${state.selectedId}/${relationKey}/${row[relation.pk]}`,
                    payload,
                );
            } else {
                await api.post(`/api/characters/${state.selectedId}/${relationKey}`, payload);
            }
            controller.close();
            showToast('Registro salvo com sucesso.', 'success');
            await loadDetails();
            renderRelationPanel(relationKey);
        } catch (error) {
            errorNode.textContent = error.message;
            errorNode.classList.remove('hidden');
        }
    });
}

async function openCharacterForm(character) {
    const resource = state.schemas.resources.characters;
    const values = character || defaultsFromColumns(resource.columns);
    const form = buildForm(resource.columns, values);
    const errorNode = el('div', { class: 'form-error hidden' });
    form.append(errorNode);

    const cancelButton = el('button', {
        type: 'button',
        class: 'btn',
        text: 'Cancelar',
        onclick: () => controller.close(),
    });

    const saveButton = el('button', { type: 'button', class: 'btn btn-primary', text: 'Salvar' });

    const controller = openModal({
        title: character ? 'Editar Personagem' : 'Novo Personagem',
        body: form,
        footer: [cancelButton, saveButton],
        wide: true,
    });

    saveButton.addEventListener('click', async () => {
        const payload = readFormValues(form);
        try {
            if (character) {
                await api.put(`/api/characters/${character.character_id}`, payload);
            } else {
                const created = await api.post('/api/characters', payload);
                state.selectedId = created.character_id;
            }
            controller.close();
            showToast('Personagem salvo com sucesso.', 'success');
            await loadCharacters();
        } catch (error) {
            errorNode.textContent = error.message;
            errorNode.classList.remove('hidden');
        }
    });
}

async function exportCharacter() {
    if (state.selectedId === null) {
        return;
    }

    try {
        const response = await fetch(`/api/characters/${state.selectedId}/export`);
        if (!response.ok) {
            let message = 'Falha ao exportar o personagem.';
            try {
                const payload = await response.json();
                message = payload.error ?? message;
            } catch (error) {
                message = `Falha ao exportar (HTTP ${response.status}).`;
            }
            throw new Error(message);
        }

        const disposition = response.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="?([^";]+)"?/);
        const filename = match ? match[1] : `personagem_${state.selectedId}.pdf`;

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = el('a', { href: url, download: filename });
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
        showToast('PDF gerado com sucesso.', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteCharacter() {
    const character = state.details.character;
    const confirmed = await confirmAction(
        `Excluir o personagem "${character.name}" e todos os seus vínculos?`,
    );
    if (!confirmed) {
        return;
    }

    try {
        await api.delete(`/api/characters/${character.character_id}`);
        state.selectedId = null;
        showToast('Personagem excluído.', 'success');
        await loadCharacters();
    } catch (error) {
        showToast(error.message, 'error');
    }
}
