"""
Script de Ingesta — Football Scout Analytics
=============================================
Trae datos de API-Football y los guarda en PostgreSQL.
Usa Pandas para limpiar y normalizar los datos antes de guardarlos.

Ligas incluidas (las 5 grandes + Eredivisie + Liga MX):
  39  → Premier League (Inglaterra)
  140 → LaLiga (España)
  135 → Serie A (Italia)
  78  → Bundesliga (Alemania)
  61  → Ligue 1 (Francia)

Uso:
  python -m scripts.ingest_data --season 2024
  python -m scripts.ingest_data --season 2024 --league 39  (solo Premier League)
"""

import argparse
import sys
import os
import pandas as pd
import numpy as np

# Permite importar desde app/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import League, Team, Player, PlayerStats
from app.api_client import APIFootballClient


# ── IDs de las ligas que vamos a sincronizar ──────────────────────────────────

TARGET_LEAGUES = {
    39:  {"name": "Premier League", "country": "England"},
    140: {"name": "La Liga",        "country": "Spain"},
    135: {"name": "Serie A",        "country": "Italy"},
    78:  {"name": "Bundesliga",     "country": "Germany"},
    61:  {"name": "Ligue 1",        "country": "France"},
}


# ─────────────────────────────────────────────────────────────────────────────
# LIMPIEZA CON PANDAS
# Aquí es donde demuestras que sabes Data Analysis, no solo guardar JSON
# ─────────────────────────────────────────────────────────────────────────────

def clean_players_dataframe(raw_players: list) -> pd.DataFrame:
    """
    Recibe la lista cruda de la API y retorna un DataFrame limpio.
    Esto es exactamente lo que hacen los Data Analysts en el trabajo real.
    """
    if not raw_players:
        return pd.DataFrame()

    rows = []
    for item in raw_players:
        p = item.get("player", {})
        # La API devuelve una lista de stats (una por liga/equipo)
        stats_list = item.get("statistics", [{}])
        s = stats_list[0] if stats_list else {}

        rows.append({
            # Datos del jugador
            "api_id":       p.get("id"),
            "name":         p.get("name"),
            "first_name":   p.get("firstname"),
            "last_name":    p.get("lastname"),
            "age":          p.get("age"),
            "birth_date":   p.get("birth", {}).get("date"),
            "nationality":  p.get("nationality"),
            "height":       p.get("height"),
            "weight":       p.get("weight"),
            "photo_url":    p.get("photo"),
            "position":     s.get("games", {}).get("position"),
            "team_api_id":  s.get("team", {}).get("id"),

            # Stats — generales
            "games_played":   s.get("games", {}).get("appearences") or 0,
            "games_started":  s.get("games", {}).get("lineups") or 0,
            "minutes_played": s.get("games", {}).get("minutes") or 0,
            "rating":         _safe_float(s.get("games", {}).get("rating")),

            # Stats — ataque
            "goals":          s.get("goals", {}).get("total") or 0,
            "xg":             _safe_float(s.get("goals", {}).get("saves")),  # xG si viene
            "shots_total":    s.get("shots", {}).get("total") or 0,
            "shots_on":       s.get("shots", {}).get("on") or 0,

            # Stats — pases
            "assists":        s.get("goals", {}).get("assists") or 0,
            "passes_total":   s.get("passes", {}).get("total") or 0,
            "passes_key":     s.get("passes", {}).get("key") or 0,
            "passes_acc":     _safe_float(s.get("passes", {}).get("accuracy")),

            # Stats — defensa
            "tackles_total":  s.get("tackles", {}).get("total") or 0,
            "interceptions":  s.get("tackles", {}).get("interceptions") or 0,
            "blocks":         s.get("tackles", {}).get("blocks") or 0,

            # Stats — duelos
            "duels_total":    s.get("duels", {}).get("total") or 0,
            "duels_won":      s.get("duels", {}).get("won") or 0,

            # Stats — dribbles
            "dribbles_att":   s.get("dribbles", {}).get("attempts") or 0,
            "dribbles_won":   s.get("dribbles", {}).get("success") or 0,

            # Stats — físico
            "fouls_drawn":    s.get("fouls", {}).get("drawn") or 0,
            "fouls_comm":     s.get("fouls", {}).get("committed") or 0,
            "yellow_cards":   s.get("cards", {}).get("yellow") or 0,
            "red_cards":      s.get("cards", {}).get("red") or 0,
        })

    df = pd.DataFrame(rows)

    # ── Limpieza ──────────────────────────────────────────────────────────

    # Elimina jugadores sin ID (datos corruptos de la API)
    df = df.dropna(subset=["api_id"])

    # Elimina duplicados (a veces la API repite jugadores)
    df = df.drop_duplicates(subset=["api_id"])

    # Normaliza posición a los 4 valores que usamos
    position_map = {
        "Goalkeeper": "goalkeeper",
        "Defender":   "defender",
        "Midfielder": "midfielder",
        "Attacker":   "attacker",
        "Forward":    "attacker",
    }
    df["position"] = df["position"].map(position_map).fillna("midfielder")

    # ── Métricas derivadas "por 90 minutos" ───────────────────────────────
    # Esta es la parte de Data Analysis: crear features nuevas desde los datos brutos

    df["minutes_per90"] = df["minutes_played"].apply(
        lambda m: round(m / 90, 2) if m > 0 else 0
    )

    # Evita división por cero usando numpy where
    min_90 = df["minutes_per90"].replace(0, np.nan)

    df["goals_per90"]      = (df["goals"]      / min_90).round(2)
    df["assists_per90"]    = (df["assists"]     / min_90).round(2)
    df["key_passes_per90"] = (df["passes_key"]  / min_90).round(2)

    # Porcentajes
    df["shot_accuracy"] = np.where(
        df["shots_total"] > 0,
        (df["shots_on"] / df["shots_total"] * 100).round(1),
        np.nan
    )
    df["duels_won_pct"] = np.where(
        df["duels_total"] > 0,
        (df["duels_won"] / df["duels_total"] * 100).round(1),
        np.nan
    )
    df["dribbles_success_pct"] = np.where(
        df["dribbles_att"] > 0,
        (df["dribbles_won"] / df["dribbles_att"] * 100).round(1),
        np.nan
    )

    # Reemplaza NaN con None para que SQLAlchemy los guarde como NULL
    df = df.where(pd.notna(df), None)

    print(f"  → DataFrame limpio: {len(df)} jugadores, {len(df.columns)} columnas")
    return df


def _safe_float(value) -> float | None:
    """Convierte a float de forma segura, retorna None si falla."""
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE GUARDADO EN DB
# ─────────────────────────────────────────────────────────────────────────────

def upsert_league(db, league_data: dict, season: int) -> League:
    """Crea o actualiza una liga. 'Upsert' = insert or update."""
    league_info = league_data.get("league", {})
    country_info = league_data.get("country", {})

    existing = db.query(League).filter(
        League.api_id == league_info["id"]
    ).first()

    if existing:
        existing.name    = league_info["name"]
        existing.country = country_info.get("name", "")
        existing.logo_url = league_info.get("logo")
        existing.season  = season
        db.commit()
        return existing

    league = League(
        api_id   = league_info["id"],
        name     = league_info["name"],
        country  = country_info.get("name", ""),
        logo_url = league_info.get("logo"),
        season   = season,
    )
    db.add(league)
    db.commit()
    db.refresh(league)
    return league


def upsert_team(db, team_data: dict, league: League) -> Team:
    """Crea o actualiza un equipo."""
    t = team_data.get("team", {})
    v = team_data.get("venue", {})

    existing = db.query(Team).filter(Team.api_id == t["id"]).first()

    if existing:
        existing.name      = t["name"]
        existing.logo_url  = t.get("logo")
        existing.league_id = league.id
        db.commit()
        return existing

    team = Team(
        api_id    = t["id"],
        name      = t["name"],
        country   = t.get("country", league.country),
        logo_url  = t.get("logo"),
        founded   = t.get("founded"),
        stadium   = v.get("name"),
        league_id = league.id,
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def upsert_player_and_stats(db, row: pd.Series, team: Team, season: int):
    """Crea o actualiza jugador + sus stats de la temporada."""

    # ── Player ────────────────────────────────────────────────
    player = db.query(Player).filter(Player.api_id == int(row["api_id"])).first()

    if not player:
        player = Player(
            api_id      = int(row["api_id"]),
            name        = row["name"],
            first_name  = row["first_name"],
            last_name   = row["last_name"],
            age         = row["age"],
            birth_date  = row["birth_date"],
            nationality = row["nationality"],
            height      = row["height"],
            weight      = row["weight"],
            photo_url   = row["photo_url"],
            position    = row["position"],
            team_id     = team.id,
        )
        db.add(player)
        db.flush()  # Necesitamos el ID antes de crear stats
    else:
        # Actualiza equipo y edad (cambian entre temporadas)
        player.team_id = team.id
        player.age     = row["age"]

    # ── PlayerStats ───────────────────────────────────────────
    stats = db.query(PlayerStats).filter(
        PlayerStats.player_id == player.id,
        PlayerStats.season    == season,
        PlayerStats.league_id == team.league_id,
    ).first()

    stats_data = {
        "games_played":          int(row["games_played"]),
        "games_started":         int(row["games_started"]),
        "minutes_played":        int(row["minutes_played"]),
        "minutes_per90":         row["minutes_per90"],
        "rating":                row["rating"],
        "goals":                 int(row["goals"]),
        "goals_per90":           row["goals_per90"],
        "shot_accuracy":         row["shot_accuracy"],
        "shots_total":           int(row["shots_total"]),
        "shots_on_target":       int(row["shots_on"]),
        "assists":               int(row["assists"]),
        "assists_per90":         row["assists_per90"],
        "passes_total":          int(row["passes_total"]),
        "passes_accuracy":       row["passes_acc"],
        "key_passes":            int(row["passes_key"]),
        "key_passes_per90":      row["key_passes_per90"],
        "tackles_total":         int(row["tackles_total"]),
        "interceptions":         int(row["interceptions"]),
        "blocks":                int(row["blocks"]),
        "duels_total":           int(row["duels_total"]),
        "duels_won":             int(row["duels_won"]),
        "duels_won_pct":         row["duels_won_pct"],
        "dribbles_attempts":     int(row["dribbles_att"]),
        "dribbles_success":      int(row["dribbles_won"]),
        "dribbles_success_pct":  row["dribbles_success_pct"],
        "fouls_drawn":           int(row["fouls_drawn"]),
        "fouls_committed":       int(row["fouls_comm"]),
        "yellow_cards":          int(row["yellow_cards"]),
        "red_cards":             int(row["red_cards"]),
    }

    if stats:
        for key, val in stats_data.items():
            setattr(stats, key, val)
    else:
        stats = PlayerStats(
            player_id = player.id,
            league_id = team.league_id,
            season    = season,
            **stats_data
        )
        db.add(stats)

    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# SCRIPT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def run_ingestion(season: int, league_filter: int | None = None):
    """
    Proceso completo:
    1. Por cada liga → guarda en DB
    2. Por cada equipo de esa liga → guarda en DB
    3. Por cada jugador del equipo → limpia con Pandas → guarda en DB
    """
    client = APIFootballClient()
    db     = SessionLocal()

    leagues_to_sync = (
        {league_filter: TARGET_LEAGUES[league_filter]}
        if league_filter else TARGET_LEAGUES
    )

    total_players = 0

    try:
        for league_api_id, league_meta in leagues_to_sync.items():
            print(f"\n{'='*55}")
            print(f"📋 Liga: {league_meta['name']} (season {season})")
            print(f"{'='*55}")

            # ── 1. Liga ───────────────────────────────────────
            print("  Obteniendo datos de la liga...")
            league_data = client.get_league(league_api_id, season)
            if not league_data:
                print(f"  ⚠️  No se encontró la liga {league_api_id}. Saltando...")
                continue

            league = upsert_league(db, league_data, season)
            print(f"  ✅ Liga guardada: {league.name}")

            # ── 2. Equipos ────────────────────────────────────
            print("  Obteniendo equipos...")
            teams_data = client.get_teams_by_league(league_api_id, season)
            print(f"  → {len(teams_data)} equipos encontrados")

            for team_data in teams_data:
                team = upsert_team(db, team_data, league)
                print(f"\n  🏟️  {team.name}")

                # ── 3. Jugadores ──────────────────────────────
                raw_players = client.get_players_by_team(team.api_id, season)

                if not raw_players:
                    print("     Sin jugadores. Saltando...")
                    continue

                # ── Aquí entra Pandas ─────────────────────────
                df = clean_players_dataframe(raw_players)

                if df.empty:
                    continue

                # Guarda cada jugador en la DB
                saved = 0
                for _, row in df.iterrows():
                    try:
                        upsert_player_and_stats(db, row, team, season)
                        saved += 1
                    except Exception as e:
                        db.rollback()
                        print(f"     ⚠️  Error con jugador {row.get('name')}: {e}")

                print(f"     → {saved}/{len(df)} jugadores guardados")
                total_players += saved

    finally:
        db.close()

    print(f"\n{'='*55}")
    print(f"✅ Ingesta completada: {total_players} jugadores guardados")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest football data from API-Football")
    parser.add_argument(
        "--season", type=int, default=2024,
        help="Season year (default: 2024)"
    )
    parser.add_argument(
        "--league", type=int, default=None,
        choices=list(TARGET_LEAGUES.keys()),
        help="Specific league ID to sync (default: all leagues)"
    )
    args = parser.parse_args()

    print(f"\n🚀 Iniciando ingesta — Season {args.season}")
    if args.league:
        print(f"   Liga: {TARGET_LEAGUES[args.league]['name']} solamente")
    else:
        print(f"   Ligas: todas ({len(TARGET_LEAGUES)})")

    run_ingestion(season=args.season, league_filter=args.league)
