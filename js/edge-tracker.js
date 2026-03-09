const CONFIG = {
    DATA_PATH: 'data/',
    LOOKBACK_DAYS: 90,
    BUCKETS: {
        props: [
            { label: '0-25%', min: 0, max: 25 },
            { label: '25-50%', min: 25, max: 50 },
            { label: '50-75%', min: 50, max: 75 },
            { label: '75-100%', min: 75, max: 100 },
            { label: '100%+', min: 100, max: Infinity }
        ],
        spread: [
            { label: '0-3%', min: 0, max: 3 },
            { label: '3-5%', min: 3, max: 5 },
            { label: '5-7.5%', min: 5, max: 7.5 },
            { label: '7.5-10%', min: 7.5, max: 10 },
            { label: '10%+', min: 10, max: Infinity }
        ],
        total: [
            { label: '0-3%', min: 0, max: 3 },
            { label: '3-5%', min: 3, max: 5 },
            { label: '5-7.5%', min: 5, max: 7.5 },
            { label: '7.5-10%', min: 7.5, max: 10 },
            { label: '10%+', min: 10, max: Infinity }
        ]
    }
};

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    loadEdgeData();
});

function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.edge-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.querySelector(`[data-panel="${btn.dataset.tab}"]`).classList.add('active');
        });
    });
}

async function loadEdgeData() {
    const dates = await discoverAvailableDates();
    const normalized = { props: [], spread: [], total: [] };

    for (const date of dates) {
        const [propsRows, teamRows] = await Promise.all([
            loadCSV(`${CONFIG.DATA_PATH}${date}_player_props.csv`),
            loadCSV(`${CONFIG.DATA_PATH}${date}_team_model.csv`)
        ]);

        propsRows.forEach(row => {
            const normalizedRow = normalizePropRow(row, date);
            if (normalizedRow) normalized.props.push(normalizedRow);
        });

        teamRows.forEach(row => {
            const normalizedRow = normalizeTeamRow(row, date);
            if (normalizedRow) normalized[normalizedRow.modelType].push(normalizedRow);
        });
    }

    ['props', 'spread', 'total'].forEach(type => {
        const summary = summarizeRows(normalized[type]);
        const buckets = bucketRows(normalized[type], CONFIG.BUCKETS[type]);
        renderSummary(type, summary);
        renderChart(type, buckets);
        renderTable(type, buckets);
    });
}

async function discoverAvailableDates() {
    const dates = [];
    const today = new Date();
    for (let i = 0; i < CONFIG.LOOKBACK_DAYS; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];
        const exists = await Promise.any([
            fileExists(`${CONFIG.DATA_PATH}${dateStr}_player_props.csv`),
            fileExists(`${CONFIG.DATA_PATH}${dateStr}_team_model.csv`)
        ]).catch(() => false);
        if (exists) dates.push(dateStr);
    }
    return dates.sort();
}

async function fileExists(path) {
    const response = await fetch(path, { method: 'HEAD' });
    return response.ok;
}

async function loadCSV(path) {
    try {
        const response = await fetch(path);
        if (!response.ok) return [];
        return parseCSV(await response.text());
    } catch {
        return [];
    }
}

function parseCSV(text) {
    const lines = text.trim().split('\n');
    if (lines.length < 2) return [];
    const headers = splitCSVLine(lines[0]).map(h => h.trim());
    return lines.slice(1).map(line => {
        const values = splitCSVLine(line);
        const row = {};
        headers.forEach((header, i) => row[header] = (values[i] || '').trim());
        return row;
    });
}

function splitCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
            inQuotes = !inQuotes;
            continue;
        }
        if (char === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    result.push(current);
    return result;
}

function normalizePropRow(row, fallbackDate) {
    const result = normalizeResult(row.result);
    if (!['win', 'loss', 'push', 'void'].includes(result)) return null;
    if (String(row.legacy || '').toLowerCase() === 'true') return null;
    if (String(row.legacy || '').toLowerCase() === 'true') return null;
    const edgePct = normalizeEdge(row.edge_pct || row.edge, row);
    const odds = toFloat(row.odds);
    const stake = toFloat(row.stake || row.units);
    const profit = toFloat(row.profit);
    if (edgePct === null || odds === null || stake === null || profit === null) return null;

    return {
        date: row.date || fallbackDate,
        modelType: 'props',
        edgePct,
        oddsDecimal: odds,
        stakeUnits: stake,
        profitUnits: profit,
        result,
        pick: `${row.player || ''} ${row.market || ''} ${row.bet || ''}`.trim(),
        sourceFile: 'player_props'
    };
}

function normalizeTeamRow(row, fallbackDate) {
    const result = normalizeResult(row.result);
    if (!['win', 'loss', 'push', 'void'].includes(result)) return null;
    if (String(row.legacy || '').toLowerCase() === 'true') return null;
    const market = (row.market || '').toUpperCase();
    let modelType = null;
    if (market === 'SPREAD') modelType = 'spread';
    else if (market === 'TOTAL') modelType = 'total';
    else return null;

    const edgePct = normalizeEdge(row.edge_pct || row.edge, row);
    const odds = toFloat(row.odds);
    const stake = toFloat(row.stake || row.units);
    const profit = toFloat(row.profit);
    if (edgePct === null || odds === null || stake === null || profit === null) return null;

    return {
        date: row.date || fallbackDate,
        modelType,
        edgePct,
        oddsDecimal: odds,
        stakeUnits: stake,
        profitUnits: profit,
        result,
        pick: row.pick || '',
        sourceFile: 'team_model'
    };
}

function normalizeResult(value) {
    const v = String(value || '').trim().toLowerCase();
    if (v === 'win' || v === 'w') return 'win';
    if (v === 'loss' || v === 'l') return 'loss';
    if (v === 'push') return 'push';
    if (v === 'void' || v === 'dnp' || v === 'dnd') return 'void';
    return 'pending';
}

function normalizeEdge(value, row = {}) {
    const n = toFloat(value);
    if (n !== null && n >= 0) return n;
    const prob = toFloat(row.prob);
    const odds = toFloat(row.odds);
    if (prob !== null && odds !== null && odds > 0) {
        return (prob - (1 / odds)) * 100;
    }
    return null;
}

function toFloat(value) {
    const n = parseFloat(value);
    return Number.isFinite(n) ? n : null;
}

function summarizeRows(rows) {
    const graded = rows.filter(r => r.result === 'win' || r.result === 'loss');
    const wins = graded.filter(r => r.result === 'win').length;
    const losses = graded.filter(r => r.result === 'loss').length;
    const stake = graded.reduce((sum, r) => sum + r.stakeUnits, 0);
    const profit = graded.reduce((sum, r) => sum + r.profitUnits, 0);
    const pushVoid = rows.filter(r => r.result === 'push' || r.result === 'void').length;
    return {
        bets: graded.length,
        wins,
        losses,
        winRate: graded.length ? (wins / graded.length) * 100 : 0,
        units: profit,
        roi: stake ? (profit / stake) * 100 : 0,
        pushVoid
    };
}

function bucketRows(rows, buckets) {
    return buckets.map(bucket => {
        const inBucket = rows.filter(r => r.edgePct >= bucket.min && r.edgePct < bucket.max);
        const graded = inBucket.filter(r => r.result === 'win' || r.result === 'loss');
        const wins = graded.filter(r => r.result === 'win').length;
        const losses = graded.filter(r => r.result === 'loss').length;
        const pushVoid = inBucket.filter(r => r.result === 'push' || r.result === 'void').length;
        const totalStake = graded.reduce((sum, r) => sum + r.stakeUnits, 0);
        const totalProfit = graded.reduce((sum, r) => sum + r.profitUnits, 0);
        const avgOdds = graded.length ? graded.reduce((sum, r) => sum + r.oddsDecimal, 0) / graded.length : 0;
        const avgEdge = inBucket.length ? inBucket.reduce((sum, r) => sum + r.edgePct, 0) / inBucket.length : 0;
        return {
            label: bucket.label,
            bets: graded.length,
            wins,
            losses,
            winRate: graded.length ? (wins / graded.length) * 100 : 0,
            units: totalProfit,
            roi: totalStake ? (totalProfit / totalStake) * 100 : 0,
            avgOdds,
            avgEdge,
            pushVoid,
            lowSample: graded.length > 0 && graded.length < 5
        };
    });
}

function renderSummary(type, summary) {
    const el = document.getElementById(`${type}Summary`);
    el.innerHTML = [
        summaryCard('Graded Bets', summary.bets),
        summaryCard('Win Rate', formatPct(summary.winRate)),
        summaryCard('Units', formatUnits(summary.units), summary.units),
        summaryCard('ROI', formatPct(summary.roi), summary.roi),
        summaryCard('Push/Void', summary.pushVoid)
    ].join('');
}

function summaryCard(label, value, signed = null) {
    const cls = signed === null ? '' : signed >= 0 ? ' style="color:#10b981"' : ' style="color:#ef4444"';
    return `<div class="summary-card"><span class="summary-label">${label}</span><span class="summary-value"${cls}>${value}</span></div>`;
}

function renderChart(type, buckets) {
    const el = document.getElementById(`${type}Chart`);
    const maxAbs = Math.max(1, ...buckets.map(b => Math.abs(b.roi)));
    el.innerHTML = buckets.map(bucket => {
        const pct = Math.max((Math.abs(bucket.roi) / maxAbs) * 160, bucket.bets ? 8 : 4);
        const barClass = bucket.roi > 0 ? 'positive' : bucket.roi < 0 ? 'negative' : 'neutral';
        return `
            <div class="bar-group ${bucket.lowSample ? 'low-sample' : ''}">
                <div class="bar-value">${bucket.bets ? formatPct(bucket.roi) : '—'}</div>
                <div class="bar ${barClass}" style="height:${pct}px"></div>
                <div class="bar-label">${bucket.label}</div>
            </div>
        `;
    }).join('');
}

function renderTable(type, buckets) {
    const el = document.getElementById(`${type}TableBody`);
    el.innerHTML = buckets.map(bucket => `
        <tr class="${bucket.lowSample ? 'low-sample' : ''}">
            <td><strong>${bucket.label}</strong></td>
            <td>${bucket.bets}</td>
            <td>${bucket.wins}</td>
            <td>${bucket.losses}</td>
            <td>${bucket.bets ? formatPct(bucket.winRate) : '—'}</td>
            <td>${bucket.bets ? formatUnits(bucket.units) : '—'}</td>
            <td>${bucket.bets ? formatPct(bucket.roi) : '—'}</td>
            <td>${bucket.bets ? bucket.avgOdds.toFixed(2) : '—'}</td>
            <td>${bucket.avgEdge ? formatPct(bucket.avgEdge) : '—'}</td>
            <td>${bucket.pushVoid}</td>
        </tr>
    `).join('');
}

function formatPct(value) {
    return `${value.toFixed(1)}%`;
}

function formatUnits(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}u`;
}