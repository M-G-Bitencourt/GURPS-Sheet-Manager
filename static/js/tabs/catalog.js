import { api } from '../api.js';
import {
    EntityManager,
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

const CATALOG_TABS = [
    { key: 'items', label: 'Itens' },
    { key: 'melee-weapons', label: 'Armas Corpo a Corpo' },
    { key: 'ranged-weapons', label: 'Armas à Distância' },
    { key: 'armor-materials', label: 'Materiais de Armadura' },
    { key: 'body-parts', label: 'Partes do Corpo' },
];

const TABLE_COLUMNS = {
    items: [
        { label: 'Nome', render: (row) => row.name },
        { label: 'Peso (kg)', class: 'text-right', render: (row) => formatNumber(row.weight) },
        { label: 'Custo ($)', class: 'text-right', render: (row) => formatNumber(row.cost) },
        { label: 'Descrição', render: (row) => truncatedText(row.description) },
    ],
    'melee-weapons': [
        { label: 'Nome', render: (row) => row.name },
        { label: 'NT', class: 'text-right', render: (row) => row.tl ?? 0 },
        { label: 'ST Min.', class: 'text-right', render: (row) => row.min_st ?? 0 },
        {
            label: 'Duas Mãos',
            render: (row) => (row.is_two_handed ? buildBadge('SIM') : '-'),
        },
        {
            label: 'Tipo',
            render: (row) => {
                const labels = [];
                if (row.is_unarmed) {
                    labels.push('DESARMADO');
                }
                if (row.is_fallback) {
                    labels.push('FALLBACK');
                }
                return labels.length ? buildBadge(labels.join(' / ')) : '-';
            },
        },
        { label: 'Peso (kg)', class: 'text-right', render: (row) => formatNumber(row.weight) },
        { label: 'Custo ($)', class: 'text-right', render: (row) => formatNumber(row.cost) },
        { label: 'Descrição', render: (row) => truncatedText(row.description) },
    ],
    'ranged-weapons': [
        { label: 'Nome', render: (row) => row.name },
        { label: 'Dano', render: (row) => row.damage ?? '-' },
        { label: 'Acc', class: 'text-right', render: (row) => row.acc ?? 0 },
        { label: 'Alcance 1/2D', class: 'text-right', render: (row) => row.range_half ?? '-' },
        { label: 'Alcance Máx.', class: 'text-right', render: (row) => row.range_max ?? '-' },
        { label: 'RoF', class: 'text-right', render: (row) => row.rof ?? 1 },
        { label: 'Tiros', render: (row) => row.shots ?? '-' },
        { label: 'ST Min.', class: 'text-right', render: (row) => row.min_st ?? 0 },
        { label: 'Rcl', class: 'text-right', render: (row) => row.recoil ?? 1 },
        { label: 'Peso (kg)', class: 'text-right', render: (row) => formatNumber(row.weight) },
        { label: 'Custo ($)', class: 'text-right', render: (row) => formatNumber(row.cost) },
    ],
    'armor-materials': [
        { label: 'Nome', render: (row) => row.name },
        { label: 'NT', class: 'text-right', render: (row) => row.tl ?? 0 },
        { label: 'RD', class: 'text-right', render: (row) => row.dr },
        {
            label: 'Flexível',
            render: (row) => (row.is_flexible ? buildBadge('SIM') : '-'),
        },
        { label: 'Custo Tronco ($)', class: 'text-right', render: (row) => formatNumber(row.cost_torso) },
        { label: 'Peso Tronco (kg)', class: 'text-right', render: (row) => formatNumber(row.weight_torso) },
        { label: 'Vestir (s)', class: 'text-right', render: (row) => row.don_time ?? 0 },
        { label: 'Notas', render: (row) => truncatedText(row.notes) },
    ],
    'body-parts': [
        { label: 'Nome', render: (row) => row.name },
        { label: 'Fator Peso/Custo', class: 'text-right', render: (row) => formatNumber(row.cost_weight_factor, 3) },
        { label: 'Ponto de Impacto', render: (row) => row.hit_location_roll ?? '-' },
        { label: 'Notas', render: (row) => truncatedText(row.notes) },
    ],
};

export function initCatalogTab(schemas) {
    const mount = document.getElementById('tab-catalog');
    clear(mount);

    mount.append(el('div', { class: 'page-header' }, [
        el('div', {}, [
            el('h1', { text: 'Equipamentos' }),
            el('div', {
                class: 'page-subtitle',
                text: 'Itens, armas corpo a corpo com modos de ataque, armas a distancia, materiais de armadura e partes do corpo.',
            }),
        ]),
    ]));

    const panels = {};
    const managers = {};
    const subtabContainer = el('div');

    const subnav = buildSubnav(CATALOG_TABS, (key) => {
        for (const [panelKey, panel] of Object.entries(panels)) {
            panel.classList.toggle('active', panelKey === key);
        }
    });

    mount.append(subnav.element, subtabContainer);

    for (const tab of CATALOG_TABS) {
        const panel = el('section', { class: 'subtab-panel', dataset: { subtab: tab.key } });
        panels[tab.key] = panel;
        subtabContainer.append(panel);

        const extraActions = tab.key === 'melee-weapons'
            ? [{ label: 'Modos', onClick: (row) => openModesModal(schemas, row) }]
            : [];

        managers[tab.key] = new EntityManager({
            schemas,
            resourceKey: tab.key,
            mount: panel,
            columns: TABLE_COLUMNS[tab.key],
            extraActions,
        });
    }

    const firstKey = CATALOG_TABS[0].key;
    subnav.setActive(firstKey);
    panels[firstKey].classList.add('active');

    for (const manager of Object.values(managers)) {
        manager.refresh().catch((error) => showToast(error.message, 'error'));
    }
}

function modeColumns(schemas) {
    return schemas.resources['melee-weapon-modes'].columns.filter(
        (column) => column.name !== 'melee_weapon_id',
    );
}

async function openModesModal(schemas, weapon) {
    const listContainer = el('div');
    const errorNode = el('div', { class: 'form-error hidden' });
    const modeLookups = { skills: [] };
    try {
        modeLookups.skills = await loadLookup('skills', 'skill_id', 'name');
    } catch (error) {
        showToast(error.message, 'error');
    }

    const addButton = el('button', {
        type: 'button',
        class: 'btn btn-primary',
        text: 'Novo Modo',
        onclick: () => openModeForm(null),
    });

    const body = el('div', { class: 'modes-modal' }, [
        el('div', { class: 'panel-title' }, [
            el('h3', { text: `Modos de Ataque - ${weapon.name}` }),
            addButton,
        ]),
        listContainer,
        errorNode,
    ]);

    const controller = openModal({
        title: 'Modos de Ataque',
        body,
        wide: true,
    });

    async function refresh() {
        try {
            const modes = await api.get(`/api/melee-weapons/${weapon.melee_weapon_id}/modes`);
            clear(listContainer);
            listContainer.append(buildTable({
                columns: [
                    { label: 'Modo', render: (row) => row.mode_name },
                    { label: 'Perícia', render: (row) => row.skill_name ?? '-' },
                    {
                        label: 'Dano',
                        render: (row) => `${row.damage_base}${row.damage_modifier >= 0 ? '+' : ''}${row.damage_modifier} ${row.damage_type}`,
                    },
                    { label: 'Mod. Ataque', class: 'text-right', render: (row) => row.attack_modifier ?? 0 },
                    { label: 'Alcance', render: (row) => row.reach },
                    { label: 'Aparar', render: (row) => row.parry },
                    { label: 'Notas', render: (row) => truncatedText(row.notes) },
                ],
                rows: modes,
                emptyMessage: 'Nenhum modo de ataque cadastrado para esta arma.',
                actions: [
                    { label: 'Editar', onClick: (mode) => openModeForm(mode) },
                    {
                        label: 'Excluir',
                        class: 'btn-danger',
                        onClick: async (mode) => {
                            const confirmed = await confirmAction(
                                `Excluir o modo "${mode.mode_name}"?`,
                            );
                            if (!confirmed) {
                                return;
                            }
                            try {
                                await api.delete(`/api/melee-weapon-modes/${mode.mode_id}`);
                                showToast('Modo excluído.', 'success');
                                await refresh();
                            } catch (error) {
                                showToast(error.message, 'error');
                            }
                        },
                    },
                ],
            }));
        } catch (error) {
            showToast(error.message, 'error');
        }
    }

    function openModeForm(mode) {
        const columns = modeColumns(schemas);
        const values = mode || defaultsFromColumns(columns);
        const form = buildForm(columns, values, modeLookups);
        const formError = el('div', { class: 'form-error hidden' });
        form.append(formError);

        const saveButton = el('button', { type: 'button', class: 'btn btn-primary', text: 'Salvar' });
        const cancelButton = el('button', {
            type: 'button',
            class: 'btn',
            text: 'Cancelar',
            onclick: () => modeController.close(),
        });

        const modeController = openModal({
            title: mode ? 'Editar Modo de Ataque' : 'Novo Modo de Ataque',
            body: form,
            footer: [cancelButton, saveButton],
            wide: true,
        });

        saveButton.addEventListener('click', async () => {
            const payload = readFormValues(form);
            try {
                if (mode) {
                    delete payload.melee_weapon_id;
                    await api.put(`/api/melee-weapon-modes/${mode.mode_id}`, payload);
                } else {
                    await api.post(`/api/melee-weapons/${weapon.melee_weapon_id}/modes`, payload);
                }
                modeController.close();
                showToast('Modo salvo com sucesso.', 'success');
                await refresh();
            } catch (error) {
                formError.textContent = error.message;
                formError.classList.remove('hidden');
            }
        });
    }

    await refresh();
}
