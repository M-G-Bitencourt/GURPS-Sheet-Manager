import { api } from '../api.js';
import { clear, el, showToast } from '../components.js';

const RELOAD_DELAY_MS = 900;

function scheduleReload(message) {
    showToast(message, 'success');
    window.setTimeout(() => window.location.reload(), RELOAD_DELAY_MS);
}

function buildSection(title, content) {
    return el('section', { class: 'panel' }, [
        el('div', { class: 'panel-title' }, [el('h2', { text: title })]),
        content,
    ]);
}

function buildBadges(entries) {
    const container = el('div', { class: 'database-badges' });
    for (const entry of entries) {
        if (entry) {
            container.append(el('span', { class: `badge ${entry.class || ''}`.trim(), text: entry.label }));
        }
    }
    return container;
}

async function browsePath(mode, input, button) {
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = 'Aguardando...';
    try {
        const result = await api.post('/api/database/browse', { mode });
        if (result && result.path) {
            input.value = result.path;
        }
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        button.disabled = false;
        button.textContent = originalLabel;
    }
}

function buildPathForm({ placeholder, hint, actionLabel, actionClass, mode, onSubmit }) {
    const input = el('input', { type: 'text', placeholder, spellcheck: 'false' });
    const errorNode = el('div', { class: 'form-error hidden' });
    const browseButton = el('button', { type: 'button', class: 'btn', text: 'Procurar...' });
    const actionButton = el('button', {
        type: 'button',
        class: `btn ${actionClass}`.trim(),
        text: actionLabel,
    });

    browseButton.addEventListener('click', () => browsePath(mode, input, browseButton));

    const form = el('form', { class: 'database-form' }, [
        el('div', { class: 'database-path-row' }, [input, browseButton, actionButton]),
    ]);
    form.addEventListener('submit', (event) => event.preventDefault());

    const run = async () => {
        errorNode.classList.add('hidden');
        const path = input.value.trim();
        if (!path) {
            errorNode.textContent = 'Informe o caminho do arquivo do banco de dados.';
            errorNode.classList.remove('hidden');
            return;
        }
        actionButton.disabled = true;
        try {
            await onSubmit(path);
        } catch (error) {
            errorNode.textContent = error.message;
            errorNode.classList.remove('hidden');
        } finally {
            actionButton.disabled = false;
        }
    };

    actionButton.addEventListener('click', run);

    return el('div', {}, [form, errorNode, el('p', { class: 'database-hint', text: hint })]);
}

async function selectDatabase(path) {
    await api.post('/api/database/select', { path });
    scheduleReload('Banco de dados aberto. Recarregando...');
}

function renderActive(state, container) {
    clear(container);

    const badges = buildBadges([
        state.is_default ? { label: 'Padrão' } : null,
        !state.exists ? { label: 'Não encontrado', class: 'badge-danger' } : null,
    ]);

    const resetButton = el('button', {
        type: 'button',
        class: 'btn',
        text: 'Usar banco padrão',
        disabled: state.is_default,
        onclick: async () => {
            try {
                await api.post('/api/database/reset');
                scheduleReload('Usando o banco padrão. Recarregando...');
            } catch (error) {
                showToast(error.message, 'error');
            }
        },
    });

    container.append(el('div', { class: 'database-active' }, [
        el('div', { class: 'database-active-info' }, [
            el('div', { class: 'database-path mono', text: state.path, title: state.path }),
            badges,
        ]),
        el('span', { class: 'spacer' }),
        resetButton,
    ]));
}

function renderRecent(state, container) {
    clear(container);

    if (!state.recent.length) {
        container.append(el('div', { class: 'empty-state', text: 'Nenhum banco de dados recente.' }));
        return;
    }

    const list = el('div', { class: 'database-recent-list' });

    for (const item of state.recent) {
        const badges = buildBadges([
            item.path === state.path ? { label: 'Atual', class: 'badge-points' } : null,
            item.path === state.default_path ? { label: 'Padrão' } : null,
            !item.exists ? { label: 'Não encontrado', class: 'badge-danger' } : null,
        ]);

        const openButton = el('button', {
            type: 'button',
            class: 'btn btn-small btn-primary',
            text: 'Abrir',
            disabled: !item.exists || item.path === state.path,
            onclick: async () => {
                try {
                    await selectDatabase(item.path);
                } catch (error) {
                    showToast(error.message, 'error');
                }
            },
        });

        const removeButton = el('button', {
            type: 'button',
            class: 'btn btn-small btn-danger',
            text: 'Remover',
            onclick: async () => {
                try {
                    await api.delete(`/api/database/recent?path=${encodeURIComponent(item.path)}`);
                    await refreshRecent(container);
                } catch (error) {
                    showToast(error.message, 'error');
                }
            },
        });

        list.append(el('div', { class: 'database-recent-item' }, [
            el('div', { class: 'database-recent-info' }, [
                el('div', { class: 'database-path mono', text: item.path, title: item.path }),
                badges,
            ]),
            el('div', { class: 'database-recent-actions' }, [openButton, removeButton]),
        ]));
    }

    container.append(list);
}

async function refreshRecent(container) {
    const state = await api.get('/api/database');
    renderRecent(state, container);
}

export function initDatabaseTab() {
    const mount = document.getElementById('tab-database');
    clear(mount);

    mount.append(el('div', { class: 'page-header' }, [
        el('div', {}, [
            el('h1', { text: 'Banco de Dados' }),
            el('div', {
                class: 'page-subtitle',
                text: 'Escolha de qual arquivo os dados são lidos, crie bancos vazios e acesse os mais recentes.',
            }),
        ]),
    ]));

    const activeContainer = el('div');
    const recentContainer = el('div');

    mount.append(
        buildSection('Banco ativo', activeContainer),
        buildSection('Abrir banco existente', buildPathForm({
            placeholder: '/caminho/para/banco.db',
            hint: 'O arquivo escolhido é validado e aberto sem ser modificado.',
            actionLabel: 'Abrir banco',
            actionClass: 'btn-primary',
            mode: 'open',
            onSubmit: selectDatabase,
        })),
        buildSection('Criar banco vazio', buildPathForm({
            placeholder: '/caminho/para/novo-banco.db',
            hint: 'O arquivo é criado com o esquema completo e sem personagens ou equipamentos.',
            actionLabel: 'Criar banco',
            actionClass: 'btn-primary',
            mode: 'save',
            onSubmit: async (path) => {
                await api.post('/api/database/create', { path });
                scheduleReload('Banco de dados criado. Recarregando...');
            },
        })),
        buildSection('Bancos recentes', recentContainer),
    );

    const refresh = async () => {
        try {
            const state = await api.get('/api/database');
            renderActive(state, activeContainer);
            renderRecent(state, recentContainer);
        } catch (error) {
            showToast(error.message, 'error');
        }
    };

    refresh();
}
