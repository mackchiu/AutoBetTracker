# Sports Money Move - Picks Tracker

A static website for tracking sports betting picks with real-time dashboard and KPIs.

## Features

- 📊 **Live Dashboard** - 8 KPI cards tracking overall, player props, and team model performance
- 📅 **Today's Picks** - Filterable view of current day's bets with status tracking
- 📈 **History** - Full pick history with date range, model, and result filters
- 🔄 **Auto-refresh** - Client-side polling every 30 seconds
- 🌙 **Dark Theme** - Sleek slate/blue design optimized for extended viewing
- 📱 **Responsive** - Works on desktop, tablet, and mobile

## Setup

### 1. Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/sportsmoneymove-tracker)

Or manually:

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### 2. Add Your Data

Create CSV files in the `/data` folder:

**`data/player_props.csv`**
```csv
date,player,market,line,projection,edge_pct,bet,confidence,role,game,odds,stake,result,profit
2024-02-26,LeBron James,Points,28.5,31.2,9.5,Over,High,Starter,LAL vs GSW,-110,100,Pending,0
```

**`data/team_model.csv`**
```csv
date,game,market,pick,line,prediction,edge,odds,stake,result,profit
2024-02-26,LAL vs GSW,Spread,LAL -3.5,-3.5,-5.2,4.8,-105,100,Win,95.24
```

### 3. Auto-Deploy

Vercel auto-deploys on every push to the `main` branch.

## CSV Schema

### Player Props
| Field | Description |
|-------|-------------|
| date | YYYY-MM-DD format |
| player | Player name |
| market | Prop market (Points, Rebounds, etc.) |
| line | Betting line |
| projection | Model projection |
| edge_pct | Edge percentage |
| bet | Over/Under or specific pick |
| confidence | High/Medium/Low |
| role | Player role |
| game | Game matchup |
| odds | American odds |
| stake | Bet amount |
| result | Win/Loss/Push/Pending |
| profit | Profit/loss amount |

### Team Model
| Field | Description |
|-------|-------------|
| date | YYYY-MM-DD format |
| game | Game matchup |
| market | Bet market (Spread, ML, Total) |
| pick | The pick |
| line | Betting line |
| prediction | Model prediction |
| edge | Edge percentage |
| odds | American odds |
| stake | Bet amount |
| result | Win/Loss/Push/Pending |
| profit | Profit/loss amount |

## Development

```bash
# Clone the repo
git clone https://github.com/yourusername/sportsmoneymove-tracker.git
cd sportsmoneymove-tracker

# Serve locally (Python 3)
python -m http.server 8000

# Or with Node.js
npx serve .
```

Visit `http://localhost:8000`

## File Structure

```
.
├── index.html          # Main HTML
├── css/
│   └── style.css       # Styles
├── js/
│   └── tracker.js      # App logic
├── data/
│   ├── player_props.csv    # Player props data
│   └── team_model.csv      # Team model data
├── vercel.json         # Vercel config
└── README.md           # This file
```

## Status Values

- **Pending** - Bet placed, game not started
- **In Progress** - Game currently playing
- **Final** - Game ended, awaiting grading
- **Graded** - Bet result confirmed
- **Win/Loss/Push** - Final graded results

## License

MIT

---

Built for Sports Money Move 🏆
