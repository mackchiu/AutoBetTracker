/**
 * Sports Money Move - Picks Tracker
 * Client-side data loading and KPI calculation
 */

// Configuration
const CONFIG = {
    REFRESH_INTERVAL: 30000, // 30 seconds
    DATA_PATHS: {
        playerProps: (date) => `data/${date}_player_props.csv`,
        teamModel: (date) => `data/${date}_team_model.csv`
    }
};

// State
let state = {
    playerProps: [],
    teamModel: [],
    lastRefresh: null
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeDatePickers();
    loadAllData();
    setupEventListeners();
    
    // Start polling
    setInterval(loadAllData, CONFIG.REFRESH_INTERVAL);
});

// Initialize date pickers with today's date
function initializeDatePickers() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('dateSelector').value = today;
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('dateSelector').addEventListener('change', filterTodayPicks);
    document.getElementById('modelFilter').addEventListener('change', filterTodayPicks);
    document.getElementById('gradeNowBtn').addEventListener('click', handleGradeNow);
}

// Load all data from CSV files
async function loadAllData() {
    try {
        const selectedDate = document.getElementById('dateSelector').value;
        const [playerProps, teamModel] = await Promise.all([
            loadCSV(CONFIG.DATA_PATHS.playerProps(selectedDate)),
            loadCSV(CONFIG.DATA_PATHS.teamModel(selectedDate))
        ]);
        
        state.playerProps = playerProps;
        state.teamModel = teamModel;
        state.lastRefresh = new Date();
        
        updateLastUpdated();
        calculateKPIs();
        filterTodayPicks();
        
        console.log('Data refreshed at', state.lastRefresh.toLocaleTimeString());
    } catch (error) {
        console.error('Error loading data:', error);
        showEmptyState();
    }
}

// Load and parse CSV file
async function loadCSV(path) {
    try {
        const response = await fetch(path);
        if (!response.ok) {
            if (response.status === 404) {
                // File doesn't exist yet, return empty array
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

// Calculate all KPIs
function calculateKPIs() {
    const allPicks = [...state.playerProps, ...state.teamModel];
    
    // Overall KPIs
    const overall = calculateStats(allPicks);
    updateKPIDisplay('totalBets', overall.totalBets);
    updateKPIDisplay('overallWinRate', formatPercent(overall.winRate));
    updateKPIDisplay('overallROI', formatPercent(overall.roi), overall.roi >= 0);
    updateKPIDisplay('overallProfit', formatCurrency(overall.profit), overall.profit >= 0);
    
    // Player Props KPIs
    const playerStats = calculateStats(state.playerProps);
    updateKPIDisplay('playerBets', playerStats.totalBets);
    updateKPIDisplay('playerWinRate', formatPercent(playerStats.winRate));
    updateKPIDisplay('playerROI', formatPercent(playerStats.roi), playerStats.roi >= 0);
    
    // Team Model KPIs
    const teamStats = calculateStats(state.teamModel);
    updateKPIDisplay('teamBets', teamStats.totalBets);
    updateKPIDisplay('teamWinRate', formatPercent(teamStats.winRate));
    updateKPIDisplay('teamROI', formatPercent(teamStats.roi), teamStats.roi >= 0);
}

// Calculate stats for a set of picks
function calculateStats(picks) {
    const totalBets = picks.length;
    if (totalBets === 0) {
        return { totalBets: 0, winRate: 0, roi: 0, profit: 0 };
    }
    
    const wins = picks.filter(p => p.result?.toLowerCase() === 'win').length;
    const losses = picks.filter(p => p.result?.toLowerCase() === 'loss').length;
    const graded = wins + losses;
    
    const winRate = graded > 0 ? (wins / graded) * 100 : 0;
    
    const totalStake = picks.reduce((sum, p) => sum + (parseFloat(p.stake) || 0), 0);
    const totalProfit = picks.reduce((sum, p) => sum + (parseFloat(p.profit) || 0), 0);
    
    const roi = totalStake > 0 ? (totalProfit / totalStake) * 100 : 0;
    
    return { totalBets, winRate, roi, profit: totalProfit };
}

// Update KPI display with optional positive/negative styling
function updateKPIDisplay(id, value, isPositive = null) {
    const element = document.getElementById(id);
    if (!element) return;
    
    element.textContent = value;
    element.classList.remove('positive', 'negative');
    
    if (isPositive === true) {
        element.classList.add('positive');
    } else if (isPositive === false) {
        element.classList.add('negative');
    }
}

// Filter and display today's picks
function filterTodayPicks() {
    const selectedDate = document.getElementById('dateSelector').value;
    const modelFilter = document.getElementById('modelFilter').value;
    
    // Filter Player Props
    let playerProps = state.playerProps.filter(p => p.date === selectedDate);
    
    // Filter Team Model
    let teamModel = state.teamModel.filter(p => p.date === selectedDate);
    
    // Apply model filter
    if (modelFilter === 'player-props') {
        teamModel = [];
    } else if (modelFilter === 'team-model') {
        playerProps = [];
    }
    
    // Update visibility
    document.getElementById('playerPropsSection').style.display = 
        modelFilter === 'team-model' ? 'none' : 'block';
    document.getElementById('teamModelSection').style.display = 
        modelFilter === 'player-props' ? 'none' : 'block';
    
    // Render tables
    renderPlayerPropsTable(playerProps);
    renderTeamModelTable(teamModel);
}

// Render Player Props table
function renderPlayerPropsTable(picks) {
    const tbody = document.getElementById('playerPropsBody');
    
    if (picks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-state">
                    <div class="empty-state-icon">🏀</div>
                    No player props for selected date
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = picks.map(pick => {
        const edge = parseFloat(pick.edge_pct) || 0;
        const edgeClass = edge > 5 ? 'edge-high' : edge > 2 ? 'edge-medium' : 'edge-low';
        const statusClass = getStatusClass(pick.result || 'pending');
        const gameShort = pick.game ? pick.game.split(' @ ').map(t => t.split(' ').pop()).join(' @ ') : '-';
        
        return `
            <tr>
                <td>${gameShort}</td>
                <td><strong>${pick.player || '-'}</strong></td>
                <td>${pick.market || '-'}</td>
                <td>${pick.line || '-'}</td>
                <td>${pick.book || '-'}</td>
                <td>${pick.projection || '-'}</td>
                <td>${pick.bet || '-'}</td>
                <td class="${edgeClass}">${edge.toFixed(1)}%</td>
                <td><span class="status ${statusClass}">${formatStatus(pick.result || 'pending')}</span></td>
            </tr>
        `;
    }).join('');
}

// Render Team Model table
function renderTeamModelTable(picks) {
    const tbody = document.getElementById('teamModelBody');
    
    if (picks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">
                    <div class="empty-state-icon">🏆</div>
                    No team model picks for selected date
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = picks.map(pick => {
        const edge = parseFloat(pick.edge) || 0;
        const edgeClass = edge > 3 ? 'edge-high' : edge > 1 ? 'edge-medium' : 'edge-low';
        const statusClass = getStatusClass(pick.result || 'pending');
        const projValue = pick.proj || '-';
        
        return `
            <tr>
                <td><strong>${pick.game || '-'}</strong></td>
                <td>${pick.pick || '-'}</td>
                <td>${projValue}</td>
                <td class="${edgeClass}">${edge.toFixed(1)}%</td>
                <td><span class="status ${statusClass}">${formatStatus(pick.result || 'pending')}</span></td>
            </tr>
        `;
    }).join('');
}

// Handle Grade Now button
function handleGradeNow() {
    const btn = document.getElementById('gradeNowBtn');
    btn.innerHTML = '<span class="loading"></span> Grading...';
    btn.disabled = true;
    
    // Simulate grading (placeholder for future implementation)
    setTimeout(() => {
        btn.innerHTML = '🔄 Grade Now';
        btn.disabled = false;
        
        // Show notification (could be replaced with toast/alert)
        console.log('Grading completed - this will be wired to backend later');
        
        // Refresh data
        loadAllData();
    }, 1500);
}

// Utility: Get CSS class for status
function getStatusClass(result) {
    const status = (result || 'pending').toLowerCase();
    switch (status) {
        case 'win': return 'status-win';
        case 'loss': return 'status-loss';
        case 'push': return 'status-push';
        case 'in progress': return 'status-progress';
        case 'final': return 'status-final';
        case 'graded': return 'status-graded';
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

// Utility: Format date for display
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Utility: Update last updated timestamp
function updateLastUpdated() {
    const element = document.getElementById('lastUpdated');
    if (state.lastRefresh) {
        element.textContent = state.lastRefresh.toLocaleTimeString();
    }
}

// Utility: Show empty state when data fails to load
function showEmptyState() {
    document.getElementById('playerPropsBody').innerHTML = `
        <tr>
            <td colspan="7" class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                Unable to load data. Ensure CSV files exist in /data folder.
            </td>
        </tr>
    `;
    document.getElementById('teamModelBody').innerHTML = `
        <tr>
            <td colspan="5" class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                Unable to load data. Ensure CSV files exist in /data folder.
            </td>
        </tr>
    `;
}
