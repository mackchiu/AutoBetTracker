/**
 * Sports Money Move - Picks History (All-Time)
 * Loads all historical CSV data for complete history view
 */

// Configuration
const CONFIG = {
    DATA_PATH: 'data/',
    KNOWN_DATES: ['2026-02-25', '2026-02-26']  // Will be auto-detected
};

// State
let state = {
    allPlayerProps: [],
    allTeamModel: [],
    allHistory: [],
    lastRefresh: null
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeDatePickers();
    loadAllHistoryData();
    setupEventListeners();
});

// Initialize date pickers
function initializeDatePickers() {
    const today = new Date().toISOString().split('T')[0];
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    
    document.getElementById('historyDateFrom').value = thirtyDaysAgo.toISOString().split('T')[0];
    document.getElementById('historyDateTo').value = today;
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('applyHistoryFilters').addEventListener('click', filterAndRenderHistory);
    document.getElementById('historyDateFrom').addEventListener('change', filterAndRenderHistory);
    document.getElementById('historyDateTo').addEventListener('change', filterAndRenderHistory);
    document.getElementById('historyModelFilter').addEventListener('change', filterAndRenderHistory);
    document.getElementById('historyResultFilter').addEventListener('change', filterAndRenderHistory);
}

// Load ALL historical data from all CSV files
async function loadAllHistoryData() {
    try {
        console.log('Loading all historical data...');
        
        // Scan for available dates by trying to load known/common date patterns
        const dates = await discoverAvailableDates();
        console.log(`Found dates: ${dates.join(', ')}`);
        
        // Load all CSV files
        const allPlayerProps = [];
        const allTeamModel = [];
        
        for (const date of dates) {
            const [playerProps, teamModel] = await Promise.all([
                loadCSV(`${CONFIG.DATA_PATH}${date}_player_props.csv`),
                loadCSV(`${CONFIG.DATA_PATH}${date}_team_model.csv`)
            ]);
            
            // Add date to each record if not present
            playerProps.forEach(p => {
                if (!p.date) p.date = date;
                p.modelType = 'Player Props';
            });
            teamModel.forEach(p => {
                if (!p.date) p.date = date;
                p.modelType = 'Team Model';
            });
            
            allPlayerProps.push(...playerProps);
            allTeamModel.push(...teamModel);
        }
        
        state.allPlayerProps = allPlayerProps;
        state.allTeamModel = allTeamModel;
        state.allHistory = [...allPlayerProps, ...allTeamModel];
        state.lastRefresh = new Date();
        
        console.log(`Loaded ${allPlayerProps.length} player props and ${allTeamModel.length} team model picks`);
        
        // Render full history
        filterAndRenderHistory();
        
    } catch (error) {
        console.error('Error loading history:', error);
        showEmptyState();
    }
}

// Discover available dates by scanning for CSV files
async function discoverAvailableDates() {
    const dates = [];
    
    // Try to load from a manifest or scan common date range
    // For now, check the last 30 days
    const today = new Date();
    for (let i = 0; i < 30; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];
        
        // Check if either file exists for this date
        const playerPropsExists = await fileExists(`${CONFIG.DATA_PATH}${dateStr}_player_props.csv`);
        const teamModelExists = await fileExists(`${CONFIG.DATA_PATH}${dateStr}_team_model.csv`);
        
        if (playerPropsExists || teamModelExists) {
            dates.push(dateStr);
        }
    }
    
    // Also check known dates from config as fallback
    for (const date of CONFIG.KNOWN_DATES) {
        if (!dates.includes(date)) {
            const exists = await fileExists(`${CONFIG.DATA_PATH}${date}_player_props.csv`) ||
                          await fileExists(`${CONFIG.DATA_PATH}${date}_team_model.csv`);
            if (exists) {
                dates.push(date);
            }
        }
    }
    
    // Sort ascending
    return dates.sort();
}

// Check if a file exists
async function fileExists(path) {
    try {
        const response = await fetch(path, { method: 'HEAD' });
        return response.ok;
    } catch (error) {
        return false;
    }
}

// Load and parse CSV file
async function loadCSV(path) {
    try {
        const response = await fetch(path);
        if (!response.ok) {
            if (response.status === 404) {
                return [];
            }
            throw new Error(`HTTP ${response.status}`);
        }
        const text = await response.text();
        return parseCSV(text);
    } catch (error) {
        console.warn(`Could not load ${path}:`, error.message);
        return [];
    }
}

// Parse CSV text into array of objects
function parseCSV(text) {
    const lines = text.trim().split('\n');
    if (lines.length < 2) return [];
    
    const headers = lines[0].split(',').map(h => h.trim());
    const data = [];
    
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim());
        const row = {};
        headers.forEach((header, index) => {
            row[header] = values[index] || '';
        });
        data.push(row);
    }
    
    return data;
}

// Filter and render history based on current filters
function filterAndRenderHistory() {
    const dateFrom = document.getElementById('historyDateFrom').value;
    const dateTo = document.getElementById('historyDateTo').value;
    const modelFilter = document.getElementById('historyModelFilter').value;
    const resultFilter = document.getElementById('historyResultFilter').value;
    
    let history = [...state.allHistory];
    
    // Apply model filter
    if (modelFilter === 'player-props') {
        history = history.filter(p => p.modelType === 'Player Props');
    } else if (modelFilter === 'team-model') {
        history = history.filter(p => p.modelType === 'Team Model');
    }
    
    // Apply date filters
    if (dateFrom) {
        history = history.filter(p => p.date >= dateFrom);
    }
    if (dateTo) {
        history = history.filter(p => p.date <= dateTo);
    }
    
    // Apply result filter
    if (resultFilter !== 'all') {
        history = history.filter(p => {
            const result = (p.result || 'pending').toLowerCase();
            return result === resultFilter;
        });
    }
    
    // Sort by date descending
    history.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    renderHistoryTable(history);
}

// Render History table
function renderHistoryTable(history) {
    const tbody = document.getElementById('historyBody');
    
    if (history.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    No picks match the selected filters
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = history.map(pick => {
        const isPlayerProp = pick.modelType === 'Player Props';
        const displayGame = pick.game || '-';
        const displayPick = isPlayerProp ?
            `${pick.player} ${pick.market} ${pick.bet} ${pick.line}` :
            `${pick.pick}`;
        const displayProj = isPlayerProp ?
            `${pick.projection}` :
            pick.proj;
        const edge = parseFloat(pick.edge_pct || pick.edge) || 0;
        const profit = parseFloat(pick.profit) || 0;
        const profitClass = profit > 0 ? 'profit-positive' : profit < 0 ? 'profit-negative' : 'profit-zero';
        const statusClass = getStatusClass(pick.result || 'pending');
        const book = pick.book || '-';
        const odds = pick.odds ? parseFloat(pick.odds).toFixed(2) : '-';

        return `
            <tr>
                <td>${formatDate(pick.date)}</td>
                <td>${pick.modelType}</td>
                <td><strong>${displayGame}</strong></td>
                <td>${displayPick || '-'}</td>
                <td>${displayProj || '-'}</td>
                <td>${book}</td>
                <td>${odds}</td>
                <td class="${edge > 3 ? 'edge-high' : edge > 1 ? 'edge-medium' : 'edge-low'}">${edge.toFixed(1)}%</td>
                <td><span class="status ${statusClass}">${formatStatus(pick.result || 'pending')}</span></td>
                <td class="${profitClass}">${formatCurrency(profit)}</td>
            </tr>
        `;
    }).join('');
}

// Utility: Get CSS class for status
function getStatusClass(result) {
    const status = (result || 'pending').toLowerCase();
    switch (status) {
        case 'win': return 'status-win';
        case 'loss': return 'status-loss';
        case 'push': return 'status-push';
        case 'pending': return 'status-pending';
        default: return 'status-pending';
    }
}

// Utility: Format status text
function formatStatus(result) {
    if (!result) return 'Pending';
    return result.charAt(0).toUpperCase() + result.slice(1).toLowerCase();
}

// Utility: Format percentage
function formatPercent(value) {
    return `${value.toFixed(1)}%`;
}

// Utility: Format currency
function formatCurrency(value) {
    const absValue = Math.abs(value);
    const sign = value >= 0 ? '+' : '-';
    return `${sign}$${absValue.toFixed(2)}`;
}

// Utility: Format date for display (handles timezone issue)
function formatDate(dateStr) {
    if (!dateStr) return '-';
    // Parse as local time by appending time component (prevents UTC shift)
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Utility: Show empty state when data fails to load
function showEmptyState() {
    document.getElementById('historyBody').innerHTML = `
        <tr>
            <td colspan="10" class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                Unable to load historical data.
            </td>
        </tr>
    `;
}
