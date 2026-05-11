# Football Scout Analytics — Backend

A data-driven football player scouting API built with FastAPI and Python. Analyzes real player statistics from top European leagues and generates proprietary scouting scores to identify transfer targets.

## 🔴 Live API
> [https://football-scout-api.onrender.com](https://football-scout-api.onrender.com)
>
> ⚠️ Hosted on Render free tier — first request may take ~30 seconds to wake up.

## 📊 Overview

This backend ingests real player data from 3 major leagues (**Premier League, Bundesliga, La Liga**) via the API-Football data source, processes it with Pandas, and applies a custom percentile-rank scoring algorithm to evaluate players by position.

The result is a REST API that powers a scouting dashboard where football clubs can discover and compare transfer targets based on actual performance data.

## ⚡ Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL (Supabase) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Data Analysis | Pandas + NumPy + SciPy |
| Data Source | API-Football |

## 🏗️ Architecture

```
API-Football
     ↓
Python Ingestion Script (Pandas)
     ↓
PostgreSQL Database
  ├── leagues
  ├── teams
  ├── players
  ├── player_stats
  └── scouting_scores
     ↓
FastAPI REST API
     ↓
React Frontend
```

## 📐 Scouting Score Algorithm

Each player receives a composite score (0–100) calculated using **percentile rank** within their position group. A score of 75 means the player performs better than 75% of players in the same position.

Scores are weighted by position:

- **Attackers** — Attack (50%) + Passing (25%) + Physical (25%)
- **Midfielders** — Passing (40%) + Attack (30%) + Defense (30%)
- **Defenders** — Defense (55%) + Physical (25%) + Passing (20%)
- **Goalkeepers** — Save metrics + Clean sheets

## 🔌 API Endpoints

```
GET /api/players                    Players list with filters & pagination
GET /api/players/{id}               Full player profile
GET /api/players/{id}/radar         Radar chart data (normalized 0-100)
GET /api/players/compare/players    Side-by-side comparison (up to 3)

GET /api/scouting/top               Top players by position
GET /api/scouting/recommendations   Transfer targets with filters
GET /api/scouting/summary           Dashboard summary stats

GET /api/leagues                    Available leagues
GET /api/leagues/{id}/teams         Teams by league
```

### Example Requests

```bash
# Best young attackers (under 25, score 65+)
GET /api/scouting/recommendations?position=attacker&max_age=25&min_score=65

# Compare 3 players
GET /api/players/compare/players?ids=27,163,445

# Top 10 midfielders
GET /api/scouting/top?position=midfielder&limit=10
```

## 🗄️ Database Schema

```
leagues ──< teams ──< players ──< player_stats
                               └──< scouting_scores
```

## 🚀 Local Development

### Prerequisites
- Python 3.12+
- PostgreSQL 16+

### Setup

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/football-scout-backend
cd football-scout-backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials and API-Football key

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

### Data Ingestion

```bash
# Ingest one league (Premier League)
python -m scripts.ingest_data --season 2024 --league 39

# Available leagues
# 39  → Premier League
# 78  → Bundesliga
# 140 → La Liga
# 135 → Serie A
# 61  → Ligue 1

# Calculate scouting scores
python -m scripts.calculate_scores --season 2024
```

## 🌍 Data Coverage

| League | Teams | Players |
|---|---|---|
| Premier League | 20 | ~500 |
| Bundesliga | 18 | ~450 |
| La Liga | 20 | ~500 |
| **Total** | **58** | **~1,450 scored** |

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py          ← FastAPI app + CORS
│   ├── database.py      ← SQLAlchemy engine + session
│   ├── models.py        ← Database models
│   ├── schemas.py       ← Pydantic request/response schemas
│   └── routers/
│       ├── players.py   ← Player endpoints
│       ├── scouting.py  ← Scouting & recommendations
│       └── leagues.py   ← League & team endpoints
├── scripts/
│   ├── ingest_data.py   ← Data ingestion with Pandas
│   ├── calculate_scores.py  ← Scouting score algorithm
│   └── test_api.py      ← API connection test
├── alembic/             ← Database migrations
├── requirements.txt
└── .env.example
```

## 👤 Author

**Jose Monterola** — Full Stack Developer
[jmonterolad.online](https://jmonterolad.online) · [LinkedIn](https://linkedin.com/in/YOUR_LINKEDIN) · [GitHub](https://github.com/YOUR_GITHUB)