import { api } from './api.js';
import { showToast } from './components.js';
import { initCharactersTab } from './tabs/characters.js';
import { initCatalogTab } from './tabs/catalog.js';
import { initDatabaseTab } from './tabs/database.js';
import { initTraitsTab } from './tabs/traits.js';

const ACTIVE_TAB_KEY = 'gurps-sheet-manager:active-tab';
const SIDEBAR_KEY = 'gurps-sheet-manager:sidebar-collapsed';
const DEFAULT_TAB = 'characters';

function activateTab(tabName) {
    for (const button of document.querySelectorAll('.nav-item')) {
        button.classList.toggle('active', button.dataset.tab === tabName);
    }
    for (const panel of document.querySelectorAll('.tab-panel')) {
        panel.classList.toggle('active', panel.dataset.tabPanel === tabName);
    }
    window.localStorage.setItem(ACTIVE_TAB_KEY, tabName);
}

function setupSidebar() {
    const toggle = document.getElementById('sidebar-toggle');
    const collapsed = window.localStorage.getItem(SIDEBAR_KEY) === '1';

    const applyState = (isCollapsed) => {
        document.body.classList.toggle('sidebar-collapsed', isCollapsed);
        toggle.textContent = isCollapsed ? '>>' : '<<';
        window.localStorage.setItem(SIDEBAR_KEY, isCollapsed ? '1' : '0');
    };

    toggle.addEventListener('click', () => {
        applyState(!document.body.classList.contains('sidebar-collapsed'));
    });

    applyState(collapsed);
}

function setupTabs() {
    for (const button of document.querySelectorAll('.nav-item')) {
        button.addEventListener('click', () => activateTab(button.dataset.tab));
    }
    const savedTab = window.localStorage.getItem(ACTIVE_TAB_KEY) || DEFAULT_TAB;
    activateTab(savedTab);
}

async function checkHealth() {
    const dot = document.getElementById('db-status');
    const label = document.getElementById('db-status-label');
    try {
        await api.get('/api/health');
        dot.classList.add('online');
        label.textContent = 'Banco conectado';
    } catch (error) {
        dot.classList.add('offline');
        label.textContent = 'Banco indisponível';
    }
}

async function main() {
    setupSidebar();
    setupTabs();

    try {
        const schemas = await api.get('/api/schemas');
        initCharactersTab(schemas);
        initCatalogTab(schemas);
        initTraitsTab(schemas);
        initDatabaseTab();
    } catch (error) {
        showToast(`Falha ao carregar esquemas: ${error.message}`, 'error');
    }

    checkHealth();
}

main();
