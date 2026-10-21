import { api } from './api.js';

export function el(tag, attributes = {}, children = []) {
    const node = document.createElement(tag);

    for (const [key, value] of Object.entries(attributes)) {
        if (value === undefined || value === null) {
            continue;
        }
        if (key === 'class') {
            node.className = value;
        } else if (key === 'text') {
            node.textContent = value;
        } else if (key === 'dataset') {
            Object.assign(node.dataset, value);
        } else if (key.startsWith('on') && typeof value === 'function') {
            node.addEventListener(key.slice(2), value);
        } else if (['checked', 'disabled', 'selected'].includes(key)) {
            node[key] = Boolean(value);
        } else {
            node.setAttribute(key, value);
        }
    }

    for (const child of [].concat(children)) {
        if (child === null || child === undefined || child === false) {
            continue;
        }
        node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }

    return node;
}

export function clear(node) {
    while (node.firstChild) {
        node.removeChild(node.firstChild);
    }
}

export function formatNumber(value, digits = 2) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    const number = Number(value);
    if (Number.isNaN(number)) {
        return String(value);
    }
    return number.toLocaleString('pt-BR', { maximumFractionDigits: digits });
}

export function buildBadge(text, className = '') {
    return el('span', { class: `badge ${className}`.trim(), text });
}

export function truncatedText(text, maxLength = 70) {
    if (text === null || text === undefined || text === '') {
        return '-';
    }
    const value = String(text);
    const node = el('span', { class: 'cell-truncate', text: value });
    node.title = value;
    if (value.length > maxLength) {
        node.textContent = `${value.slice(0, maxLength)}...`;
    }
    return node;
}

export function showToast(message, type = 'info') {
    const root = document.getElementById('toast-root');
    const toast = el('div', { class: `toast ${type}`, text: message });
    root.append(toast);
    setTimeout(() => toast.remove(), 3400);
}

export function openModal({ title, body, footer = [], wide = false, onClose = null }) {
    const root = document.getElementById('modal-root');
    const overlay = el('div', { class: 'modal-overlay' });

    const close = () => {
        overlay.remove();
        document.removeEventListener('keydown', handleKey);
        if (onClose) {
            onClose();
        }
    };

    const handleKey = (event) => {
        if (event.key === 'Escape') {
            close();
        }
    };

    const closeButton = el('button', {
        type: 'button',
        class: 'modal-close',
        text: 'X',
        title: 'Fechar',
        onclick: close,
    });

    const modal = el('div', { class: `modal${wide ? ' modal-wide' : ''}` }, [
        el('div', { class: 'modal-header' }, [el('h2', { text: title }), closeButton]),
        el('div', { class: 'modal-body' }, [body]),
        footer.length ? el('div', { class: 'modal-footer' }, footer) : null,
    ]);

    overlay.append(modal);
    overlay.addEventListener('mousedown', (event) => {
        if (event.target === overlay) {
            close();
        }
    });
    document.addEventListener('keydown', handleKey);
    root.append(overlay);

    return { close, modal };
}

export function confirmAction(message, confirmLabel = 'Excluir') {
    return new Promise((resolve) => {
        const cancelButton = el('button', {
            type: 'button',
            class: 'btn',
            text: 'Cancelar',
            onclick: () => {
                controller.close();
                resolve(false);
            },
        });

        const confirmButton = el('button', {
            type: 'button',
            class: 'btn btn-danger',
            text: confirmLabel,
            onclick: () => {
                controller.close();
                resolve(true);
            },
        });

        const body = el('p', { class: 'confirm-message', text: message });
        const controller = openModal({
            title: 'Confirmar operação',
            body,
            footer: [cancelButton, confirmButton],
        });
    });
}

export function readFormValues(form) {
    const values = {};
    for (const element of form.elements) {
        if (!element.name || element.disabled) {
            continue;
        }
        if (element.type === 'checkbox') {
            values[element.name] = element.checked ? 1 : 0;
        } else if (element.value === '') {
            values[element.name] = null;
        } else {
            values[element.name] = element.value;
        }
    }
    return values;
}

function buildLabel(column, inputId) {
    return el('label', { for: inputId }, [
        column.label,
        column.required ? el('span', { class: 'required-mark', text: ' *' }) : null,
    ]);
}

function buildField(column, value, lookups) {
    const inputId = `field-${column.name}-${Math.random().toString(36).slice(2, 8)}`;

    if (column.type === 'bool') {
        const checkbox = el('input', { type: 'checkbox', name: column.name, id: inputId });
        checkbox.checked = Boolean(value);
        checkbox.disabled = Boolean(column.read_only);
        return el('div', { class: 'form-field checkbox-field' }, [
            checkbox,
            el('label', { for: inputId, text: column.label }),
        ]);
    }

    let input;
    let extra = null;

    if (column.type === 'fk') {
        input = el('select', { name: column.name, id: inputId });
        input.append(el('option', { value: '', text: '-- Selecione --' }));
        const options = lookups[column.fk_resource] || [];
        for (const option of options) {
            const optionNode = el('option', { value: String(option.value), text: option.label });
            if (value !== null && value !== undefined && String(value) === String(option.value)) {
                optionNode.selected = true;
            }
            input.append(optionNode);
        }
        const hasValue = value !== null && value !== undefined && String(value) !== '';
        if (hasValue && !options.some((option) => String(option.value) === String(value))) {
            const missing = el('option', { value: String(value), text: `#${value}` });
            missing.selected = true;
            input.append(missing);
        }
    } else if (column.type === 'select') {
        input = el('select', { name: column.name, id: inputId });
        if (!column.required) {
            input.append(el('option', { value: '', text: '-- Selecione --' }));
        }
        const options = [...column.options];
        const hasValue = value !== null && value !== undefined && String(value) !== '';
        if (hasValue && !options.includes(String(value))) {
            options.push(String(value));
        }
        for (const option of options) {
            const optionNode = el('option', { value: option, text: option });
            if (hasValue && String(value) === option) {
                optionNode.selected = true;
            }
            input.append(optionNode);
        }
    } else if (column.type === 'enum') {
        const listId = `${inputId}-list`;
        input = el('input', { type: 'text', name: column.name, id: inputId, list: listId });
        input.value = value ?? '';
        const datalist = el('datalist', { id: listId });
        const options = [...column.options];
        if (value && !options.includes(value)) {
            options.push(value);
        }
        for (const option of options) {
            datalist.append(el('option', { value: option }));
        }
        extra = datalist;
    } else if (column.multiline) {
        input = el('textarea', { name: column.name, id: inputId });
        input.value = value ?? '';
    } else {
        const inputType = ['int', 'float'].includes(column.type) ? 'number' : 'text';
        input = el('input', { type: inputType, name: column.name, id: inputId });
        if (column.type === 'float') {
            input.step = 'any';
        }
        if (column.type === 'int') {
            input.step = '1';
        }
        input.value = value ?? '';
    }

    input.disabled = Boolean(column.read_only);

    const fieldClass = column.multiline ? 'form-field span-2' : 'form-field';
    return el('div', { class: fieldClass }, [buildLabel(column, inputId), input, extra]);
}

export function buildForm(columns, values = {}, lookups = {}) {
    const form = el('form', { class: 'entity-form' });
    form.addEventListener('submit', (event) => event.preventDefault());
    for (const column of columns) {
        form.append(buildField(column, values[column.name], lookups));
    }
    return form;
}

export function defaultsFromColumns(columns) {
    const values = {};
    for (const column of columns) {
        if (column.type === 'bool') {
            values[column.name] = column.default ? 1 : 0;
        } else {
            values[column.name] = column.default ?? '';
        }
    }
    return values;
}

export function buildTable({
    columns,
    rows,
    emptyMessage = 'Nenhum registro encontrado.',
    actions = [],
    onRowClick = null,
}) {
    if (!rows.length) {
        return el('div', { class: 'empty-state', text: emptyMessage });
    }

    const headerCells = columns.map((column) => el('th', { class: column.class || '', text: column.label }));
    if (actions.length) {
        headerCells.push(el('th', { class: 'actions-cell', text: 'Ações' }));
    }

    const tbody = el('tbody');
    for (const row of rows) {
        const cells = columns.map((column) => {
            const cell = el('td', { class: column.class || '' });
            const content = column.render(row);
            if (content instanceof Node) {
                cell.append(content);
            } else {
                cell.textContent = content ?? '';
            }
            return cell;
        });

        if (actions.length) {
            const cell = el('td', { class: 'actions-cell' });
            for (const action of actions) {
                if (action.visible && !action.visible(row)) {
                    continue;
                }
                cell.append(el('button', {
                    type: 'button',
                    class: `btn btn-small ${action.class || ''}`.trim(),
                    text: typeof action.label === 'function' ? action.label(row) : action.label,
                    onclick: () => action.onClick(row),
                }));
            }
            cells.push(cell);
        }

        const tableRow = el('tr', { class: onRowClick ? 'clickable-row' : '' }, cells);
        if (onRowClick) {
            tableRow.addEventListener('click', (event) => {
                if (event.target.closest('button, input, select, textarea, a')) {
                    return;
                }
                onRowClick(row);
            });
        }
        tbody.append(tableRow);
    }

    return el('div', { class: 'table-wrapper' }, [
        el('table', { class: 'data-table' }, [el('thead', {}, [el('tr', {}, headerCells)]), tbody]),
    ]);
}

export function buildSubnav(items, onChange) {
    const container = el('div', { class: 'subnav' });
    const buttons = new Map();
    let current = null;

    const setActive = (key) => {
        current = key;
        for (const [itemKey, button] of buttons) {
            button.classList.toggle('active', itemKey === key);
        }
    };

    for (const item of items) {
        const button = el('button', {
            type: 'button',
            class: 'subnav-item',
            text: item.label,
            onclick: () => {
                if (current === item.key) {
                    return;
                }
                setActive(item.key);
                onChange(item.key);
            },
        });
        buttons.set(item.key, button);
        container.append(button);
    }

    return { element: container, setActive };
}

const lookupCache = new Map();

export function loadLookup(resourceKey, valueColumn, labelColumn) {
    const cacheKey = `${resourceKey}:${valueColumn}:${labelColumn}`;
    if (!lookupCache.has(cacheKey)) {
        const promise = api.get(`/api/${resourceKey}`).then((rows) => rows.map((row) => ({
            value: row[valueColumn],
            label: String(row[labelColumn] ?? `#${row[valueColumn]}`),
        })));
        lookupCache.set(cacheKey, promise);
    }
    return lookupCache.get(cacheKey);
}

export function invalidateLookups() {
    lookupCache.clear();
}

export class EntityManager {
    constructor({
        schemas,
        resourceKey,
        mount,
        columns,
        createLabel = 'Novo Registro',
        emptyMessage = 'Nenhum registro encontrado.',
        extraActions = [],
        prepare = null,
        prepareForm = null,
    }) {
        this.schemas = schemas;
        this.resource = schemas.resources[resourceKey];
        this.mount = mount;
        this.columns = columns;
        this.createLabel = createLabel;
        this.emptyMessage = emptyMessage;
        this.extraActions = extraActions;
        this.prepare = prepare;
        this.prepareForm = prepareForm;
        this.rows = [];
        this.searchTerm = '';
        this.tableContainer = el('div');
        this.buildLayout();
    }

    buildLayout() {
        clear(this.mount);

        const createButton = el('button', {
            type: 'button',
            class: 'btn btn-primary',
            text: this.createLabel,
            onclick: () => this.openForm(null),
        });

        const toolbar = el('div', { class: 'toolbar' });
        if (this.resource.search_columns.length) {
            const search = el('input', {
                type: 'search',
                class: 'search-input',
                placeholder: 'Buscar...',
            });
            search.addEventListener('input', () => {
                this.searchTerm = search.value.trim().toLowerCase();
                this.renderTable();
            });
            toolbar.append(search);
        }
        toolbar.append(el('span', { class: 'spacer' }), createButton);

        this.mount.append(toolbar, this.tableContainer);
    }

    filteredRows() {
        if (!this.searchTerm || !this.resource.search_columns.length) {
            return this.rows;
        }
        return this.rows.filter((row) => this.resource.search_columns.some((column) => (
            String(row[column] ?? '').toLowerCase().includes(this.searchTerm)
        )));
    }

    renderTable() {
        clear(this.tableContainer);
        const actions = [
            { label: 'Editar', onClick: (row) => this.openForm(row) },
            ...this.extraActions,
            { label: 'Excluir', class: 'btn-danger', onClick: (row) => this.remove(row) },
        ];
        this.tableContainer.append(buildTable({
            columns: this.columns,
            rows: this.filteredRows(),
            emptyMessage: this.emptyMessage,
            actions,
        }));
    }

    async refresh() {
        if (this.prepare) {
            await this.prepare();
        }
        this.rows = await api.get(`/api/${this.resource.key}`);
        this.renderTable();
    }

    async openForm(row) {
        const lookups = {};
        for (const column of this.resource.columns) {
            if (column.type === 'fk' && column.fk_resource) {
                const target = this.schemas.resources[column.fk_resource];
                lookups[column.fk_resource] = await loadLookup(
                    column.fk_resource,
                    target.pk,
                    column.fk_label,
                );
            }
        }

        const values = row || defaultsFromColumns(this.resource.columns);
        const form = buildForm(this.resource.columns, values, lookups);
        if (this.prepareForm) {
            this.prepareForm(form, values);
        }
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
            title: row
                ? `Editar - ${this.resource.label}`
                : `Novo registro - ${this.resource.label}`,
            body: form,
            footer: [cancelButton, saveButton],
            wide: true,
        });

        saveButton.addEventListener('click', async () => {
            const payload = readFormValues(form);
            try {
                if (row) {
                    await api.put(`/api/${this.resource.key}/${row[this.resource.pk]}`, payload);
                } else {
                    await api.post(`/api/${this.resource.key}`, payload);
                }
                controller.close();
                invalidateLookups();
                showToast('Registro salvo com sucesso.', 'success');
                await this.refresh();
            } catch (error) {
                errorNode.textContent = error.message;
                errorNode.classList.remove('hidden');
            }
        });
    }

    async remove(row) {
        const label = row.name ?? row.class ?? row.stat ?? `#${row[this.resource.pk]}`;
        const confirmed = await confirmAction(
            `Excluir "${label}"? Esta operação não pode ser desfeita.`,
        );
        if (!confirmed) {
            return;
        }
        try {
            await api.delete(`/api/${this.resource.key}/${row[this.resource.pk]}`);
            invalidateLookups();
            showToast('Registro excluído.', 'success');
            await this.refresh();
        } catch (error) {
            showToast(error.message, 'error');
        }
    }
}
