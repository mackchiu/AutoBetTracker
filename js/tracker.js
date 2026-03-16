/**
 * Sports Money Move - Picks Tracker (Main Dashboard)
 * Shows all-time KPIs + today's picks
 */

// Configuration
const CONFIG = {
    REFRESH_INTERVAL: 30000, // 30 seconds
    DATA_PATH: 'data/'
};

// State
let state = {
    allPlayerProps: [],
    allTeamModel: [],
    todayPlayerProps: [],
    todayTeamModel: [],
    todayMoneyline: [],
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

// Initialize date pickers with today's date (Eastern Time)
function initializeDatePickers() {
    const now = new Date();
    const easternTime = new Date(now.toLocaleString("en-US", {timeZone: "America/New_York"}));
    const year = easternTime.getFullYear();
    const month = String(easternTime.getMonth() + 1).padStart(2, '0');
    const day = String(easternTime.getDate()).padStart(2, '0');
    const today = `${year}-${month}-${day}`;
    document.getElementById('dateSelector').value = today;
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('dateSelector').addEventListener('change', filterTodayPicks);
    document.getElementById('modelFilter').addEventListener('change', filterTodayPicks);
    document.getElementById('gradeNowBtn').addEventListener('click', handleGradeNow);
}

// Load all historical data for KPIs + today's data for tables
async function loadAllData() {
    try {
        const today = document.getElementById('dateSelector').value;
        
        // Load all historical data for KPIs
        const dates = await discoverAvailableDates();
        
        const allPlayerProps = [];
        const allTeamModel = [];
        const allMoneyline = [];
        
        for (const date of dates) {
            const sourcePaths = getDataSourcePaths(date, today);
            const [playerProps, teamModel] = await Promise.all([
                loadCSV(...sourcePaths.playerProps),
                loadCSV(...sourcePaths.teamModel)
            ]);
            
            playerProps.forEach(p => { if (!p.date) p.date = date; });
            teamModel.forEach(p => { if (!p.date) p.date = date; });

            const activePlayerProps = playerProps.filter(p => String(p.legacy || '').toLowerCase() !== 'true');
            const activeTeamModel = teamModel.filter(p => String(p.legacy || '').toLowerCase() !== 'true');
            
            const activeMoneyline = activeTeamModel.filter(p => (p.market || '').toUpperCase() === 'MONEYLINE');
            const activeNonMoneyline = activeTeamModel.filter(p => (p.market || '').toUpperCase() !== 'MONEYLINE');
            allPlayerProps.push(...activePlayerProps);
            allTeamModel.push(...activeNonMoneyline);
            allMoneyline.push(...activeMoneyline);
        }
        
        state.allPlayerProps = allPlayerProps;
        state.allTeamModel = allTeamModel;
        state.allMoneyline = allMoneyline;
        state.todayPlayerProps = allPlayerProps.filter(p => p.date === today);
        state.todayTeamModel = allTeamModel.filter(p => p.date === today);
        state.todayMoneyline = allMoneyline.filter(p => p.date === today);
        state.lastRefresh = new Date();
        
        updateLastUpdated();
        calculateKPIs(); // Uses all historical data
        filterTodayPicks(); // Shows only today's picks
        
        console.log('Data refreshed at', state.lastRefresh.toLocaleTimeString());
    } catch (error) {
        console.error('Error loading data:', error);
        showEmptyState();
    }
}

// Discover available dates by scanning for CSV files
async function discoverAvailableDates() {
    const dates = [];
    const today = new Date();
    
    for (let i = 0; i < 60; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];
        
        const sourcePaths = getDataSourcePaths(dateStr, document.getElementById('dateSelector')?.value || dateStr);
        let playerPropsExists = false;
        for (const path of sourcePaths.playerProps) { if (await fileExists(path)) { playerPropsExists = true; break; } }
        let teamModelExists = false;
        for (const path of sourcePaths.teamModel) { if (await fileExists(path)) { teamModelExists = true; break; } }
        
        if (playerPropsExists || teamModelExists) {
            dates.push(dateStr);
        }
    }
    
    return dates.sort();
}

function getDataSourcePaths(date, today) {
    const isToday = date === today;
    if (isToday) {
        return {
            playerProps: [
                `${CONFIG.DATA_PATH}final/${date}_player_props_final.csv`,
                `${CONFIG.DATA_PATH}raw/${date}_player_props_raw.csv`,
                `${CONFIG.DATA_PATH}${date}_player_props.csv`
            ],
            teamModel: [
                `${CONFIG.DATA_PATH}final/${date}_team_model_final.csv`,
                `${CONFIG.DATA_PATH}raw/${date}_team_model_raw.csv`,
                `${CONFIG.DATA_PATH}${date}_team_model.csv`
            ]
        };
    }
    return {
        playerProps: [
            `${CONFIG.DATA_PATH}graded/${date}_player_props_graded.csv`,
            `${CONFIG.DATA_PATH}${date}_player_props.csv`
        ],
        teamModel: [
            `${CONFIG.DATA_PATH}graded/${date}_team_model_graded.csv`,
            `${CONFIG.DATA_PATH}${date}_team_model.csv`
        ]
    };
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
async function loadCSV(...paths) {
    for (const path of paths) {
        try {
            const response = await fetch(path);
        if (!response.ok) {
            if (response.status === 404) continue;
            throw new Error(`HTTP ${response.status}`);
        }
            const text = await response.text();
            return parseCSV(text);
        } catch (error) {
            console.warn(`Could not load ${path}:`, error.message);
        }
    }
    return [];
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

// Calculate all KPIs using ALL historical data
function calculateKPIs() {
    const allPicks = [...state.allPlayerProps, ...state.allTeamModel];
    
    // Overall KPIs
    const overall = calculateStats(allPicks);
    updateKPIDisplay('totalBets', overall.totalBets);
    updateKPIDisplay('overallWinRate', formatPercent(overall.winRate));
    updateKPIDisplay('overallROI', formatPercent(overall.roi), overall.roi >= 0);
    updateKPIDisplay('overallProfit', formatCurrency(overall.profit), overall.profit >= 0);
    
    // Player Props KPIs (all-time)
    const playerStats = calculateStats(state.allPlayerProps);
    updateKPIDisplay('playerBets', playerStats.totalBets);
    updateKPIDisplay('playerWinRate', formatPercent(playerStats.winRate));
    updateKPIDisplay('playerROI', formatPercent(playerStats.roi), playerStats.roi >= 0);
    
    // Team Model KPIs (all-time, excluding moneyline)
    const teamStats = calculateStats(state.allTeamModel);
    updateKPIDisplay('teamBets', teamStats.totalBets);
    updateKPIDisplay('teamWinRate', formatPercent(teamStats.winRate));
    updateKPIDisplay('teamROI', formatPercent(teamStats.roi), teamStats.roi >= 0);

    // Moneyline KPIs
    const mlStats = calculateStats(state.allMoneyline || []);
    updateKPIDisplay('mlBets', mlStats.totalBets);
    updateKPIDisplay('mlWinRate', formatPercent(mlStats.winRate));
    updateKPIDisplay('mlROI', formatPercent(mlStats.roi), mlStats.roi >= 0);
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

// Update KPI display
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

// Filter and display today's picks only
function filterTodayPicks() {
    const selectedDate = document.getElementById('dateSelector').value;
    const modelFilter = document.getElementById('modelFilter').value;
    
    // Filter from all data
    let playerProps = state.allPlayerProps.filter(p => p.date === selectedDate);
    let teamModel = state.allTeamModel.filter(p => p.date === selectedDate && (p.market || '').toUpperCase() !== 'MONEYLINE');
    let moneyline = state.allTeamModel.filter(p => p.date === selectedDate && (p.market || '').toUpperCase() === 'MONEYLINE');
    
    // Apply model filter
    if (modelFilter === 'player-props') {
        teamModel = [];
        moneyline = [];
    } else if (modelFilter === 'team-model') {
        playerProps = [];
        moneyline = [];
    }
    
    // Update visibility
    document.getElementById('playerPropsSection').style.display = 
        modelFilter === 'team-model' ? 'none' : 'block';
    document.getElementById('teamModelSection').style.display = 
        modelFilter === 'player-props' ? 'none' : 'block';
    document.getElementById('moneylineSection').style.display = 
        modelFilter === 'player-props' ? 'none' : 'block';
    
    // Render tables
    renderPlayerPropsTable(playerProps);
    renderTeamModelTable(teamModel);
    renderMoneylineTable(moneyline);
}

function normalizeEdgeDisplay(pick) {
    const explicit = parseFloat(pick.edge_pct ?? pick.edge);
    if (Number.isFinite(explicit)) return explicit;
    const prob = parseFloat(pick.prob);
    const odds = parseFloat(pick.odds);
    if (Number.isFinite(prob) && Number.isFinite(odds) && odds > 0) {
        return (prob - (1 / odds)) * 100;
    }
    return 0;
}

// Render Player Props table
function renderPlayerPropsTable(picks) {
    const tbody = document.getElementById('playerPropsBody');

    if (picks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" class="empty-state">
                    <div class="empty-state-icon">🏀</div>
                    No player props for selected date
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = picks.map(pick => {
        const edge = normalizeEdgeDisplay(pick);
        const edgeClass = edge > 5 ? 'edge-high' : edge > 2 ? 'edge-medium' : 'edge-low';
        const statusClass = getStatusClass(pick.result || 'pending');
        const gameShort = pick.game ? pick.game.split(' @ ').map(t => t.split(' ').pop()).join(' @ ') : '-';
        const odds = pick.odds ? parseFloat(pick.odds).toFixed(2) : '-';
        const units = parseFloat(pick.stake) || 0;
        const unitsDisplay = units > 0 ? units.toFixed(2) : '-';  // Kelly precision: 2 decimals

        return `
            <tr>
                <td>${gameShort}</td>
                <td><strong>${pick.player || '-'}</strong></td>
                <td>${pick.market || '-'}</td>
                <td>${pick.line || '-'}</td>
                <td>${pick.book || '-'}</td>
                <td>${pick.projection || '-'}</td>
                <td>${pick.bet || '-'}</td>
                <td>${odds}</td>
                <td class="${edgeClass}">${edge.toFixed(1)}%</td>
                <td>${unitsDisplay}</td>
                <td><span class="status ${statusClass}">${formatStatus(pick.result || 'pending')}</span></td>
            </tr>
        `;
    }).join('');
}

// Render Team Model table
function renderSignalIcons(pick) {
    const parts = [];
    if (pick.line_movement_flag) parts.push(pick.line_movement_flag);
    if (pick.sharp_flag) parts.push(pick.sharp_flag);
    if (pick.divergence_flag) parts.push(pick.divergence_flag);
    if (pick.conflict_flag) parts.push(pick.conflict_flag);
    return parts.length ? parts.join(' ') : '—';
}

function renderTeamModelTable(picks) {
    const tbody = document.getElementById('teamModelBody');

    if (picks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
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
        const odds = pick.odds ? parseFloat(pick.odds).toFixed(2) : '-';
        const units = parseFloat(pick.stake) || 0;
        const unitsDisplay = units > 0 ? units.toFixed(2) : '-';
        
        // Parse projection and show favored side (negative spread) only
        let projValue = pick.proj || '-';
        if (projValue !== '-' && pick.game) {
            const match = projValue.match(/^(.+?)\s+([+-]?\d+\.?\d*)$/);
            if (match) {
                const projTeam = match[1];
                const projSpread = parseFloat(match[2]);
                const teams = pick.game.split(' @ ');
                if (teams.length === 2) {
                    const awayTeam = teams[0];
                    const homeTeam = teams[1];
                    // If projection is positive (underdog), show the other team as favored
                    if (projSpread > 0) {
                        const favoredTeam = projTeam === homeTeam ? awayTeam : homeTeam;
                        projValue = `${favoredTeam} -${projSpread.toFixed(1)}`;
                    } else if (projSpread < 0) {
                        // Already favored, show as-is
                        projValue = `${projTeam} ${projSpread.toFixed(1)}`;
                    }
                }
            }
        }

        return `
            <tr>
                <td><strong>${pick.game || '-'}</strong></td>
                <td>${pick.pick || '-'}</td>
                <td>${projValue}</td>
                <td>${pick.book || '-'}</td>
                <td>${odds}</td>
                <td class="${edgeClass}">${edge.toFixed(1)}%</td>
                <td>${unitsDisplay}</td>
                <td><span class="status ${statusClass}">${formatStatus(pick.result || 'pending')}</span></td>
            </tr>
        `;
    }).join('');
}


function renderMoneylineTable(picks) {
    const tbody = document.getElementById('moneylineBody');
    if (picks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    <div class="empty-state-icon">💰</div>
                    No moneyline value picks for selected date
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = picks.map(pick => {
        const statusClass = getStatusClass(pick.result || 'pending');
        const units = parseFloat(pick.stake) || 0;
        const unitsDisplay = units > 0 ? units.toFixed(2) : '-';
        const pickText = pick.pick || pick.ml_candidate || '-';
        let winProb = '-';
        if (pick.pick && pick.pick.includes('ML')) {
            const team = pick.pick.replace(' ML','');
            if (pick.game && pick.game.split(' @ ')[1] === team && pick.home_ml_prob) {
                winProb = `${(parseFloat(pick.home_ml_prob) * 100).toFixed(1)}%`;
            } else if (pick.away_ml_prob) {
                winProb = `${(parseFloat(pick.away_ml_prob) * 100).toFixed(1)}%`;
            }
        }
        let edge = '-';
        if (pick.pick && pick.pick.includes('ML')) {
            const team = pick.pick.replace(' ML','');
            if (pick.game && pick.game.split(' @ ')[1] === team && pick.home_ml_edge !== undefined) {
                edge = `${parseFloat(pick.home_ml_edge).toFixed(1)}%`;
            } else if (pick.away_ml_edge !== undefined) {
                edge = `${parseFloat(pick.away_ml_edge).toFixed(1)}%`;
            }
        }
        return `
            <tr>
                <td><strong>${pick.game || '-'}</strong></td>
                <td>${pickText}</td>
                <td>${winProb}</td>
                <td class="edge-high">${edge}</td>
                <td>${unitsDisplay}</td>
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
    
    setTimeout(() => {
        btn.innerHTML = '🔄 Grade Now';
        btn.disabled = false;
        console.log('Grading completed - this will be wired to backend later');
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
