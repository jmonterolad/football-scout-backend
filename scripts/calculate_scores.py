import argparse
import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Player, PlayerStats, ScoutingScore
from sqlalchemy import text


def load_stats_dataframe(season: int) -> pd.DataFrame:
    query = """
        SELECT
            p.id AS player_id, p.name, p.position, p.nationality, p.age,
            t.name AS team_name, l.name AS league_name,
            ps.games_played, ps.minutes_played, ps.minutes_per90, ps.rating,
            ps.goals, ps.goals_per90, ps.xg, ps.xg_per90, ps.shots_total, ps.shot_accuracy,
            ps.assists, ps.assists_per90, ps.xa, ps.xa_per90, ps.passes_accuracy,
            ps.key_passes, ps.key_passes_per90, ps.tackles_total, ps.tackles_success,
            ps.interceptions, ps.blocks, ps.duels_won_pct, ps.aerial_won_pct,
            ps.dribbles_success_pct, ps.yellow_cards, ps.red_cards, ps.fouls_committed,
            ps.saves, ps.saves_pct, ps.clean_sheets, ps.goals_conceded
        FROM players p
        JOIN player_stats ps ON ps.player_id = p.id
        JOIN teams t ON p.team_id = t.id
        JOIN leagues l ON ps.league_id = l.id
        WHERE ps.season = :season AND ps.minutes_played >= 90
        ORDER BY p.position, ps.minutes_played DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"season": season})
    print(f"  -> {len(df)} jugadores cargados para temporada {season}")
    print(f"  -> Posiciones: {df['position'].value_counts().to_dict()}")
    return df


def percentile_rank(series: pd.Series, ascending: bool = True) -> pd.Series:
    clean = series.fillna(0)
    if not ascending:
        clean = clean.max() - clean
    return (clean.rank(pct=True, method='average') * 100).round(1)


def calculate_attacker_scores(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["attack_score"]  = (percentile_rank(d["goals_per90"])*0.45 + percentile_rank(d["xg_per90"])*0.35 + percentile_rank(d["shot_accuracy"])*0.20).round(1)
    d["passing_score"] = (percentile_rank(d["assists_per90"])*0.40 + percentile_rank(d["xa_per90"])*0.35 + percentile_rank(d["key_passes_per90"])*0.25).round(1)
    d["physical_score"]= (percentile_rank(d["dribbles_success_pct"])*0.45 + percentile_rank(d["duels_won_pct"])*0.35 + percentile_rank(d["yellow_cards"], ascending=False)*0.20).round(1)
    d["overall_score"] = (d["attack_score"]*0.50 + d["passing_score"]*0.25 + d["physical_score"]*0.25).round(1)
    d["defense_score"] = None
    return d


def calculate_midfielder_scores(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["passing_score"] = (percentile_rank(d["passes_accuracy"])*0.30 + percentile_rank(d["key_passes_per90"])*0.30 + percentile_rank(d["xa_per90"])*0.25 + percentile_rank(d["assists_per90"])*0.15).round(1)
    d["attack_score"]  = (percentile_rank(d["goals_per90"])*0.50 + percentile_rank(d["xg_per90"])*0.50).round(1)
    d["defense_score"] = (percentile_rank(d["tackles_total"])*0.35 + percentile_rank(d["interceptions"])*0.35 + percentile_rank(d["duels_won_pct"])*0.30).round(1)
    d["overall_score"] = (d["passing_score"]*0.40 + d["attack_score"]*0.30 + d["defense_score"]*0.30).round(1)
    d["physical_score"]= None
    return d


def calculate_defender_scores(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["defense_score"] = (percentile_rank(d["tackles_total"])*0.25 + percentile_rank(d["tackles_success"])*0.20 + percentile_rank(d["interceptions"])*0.25 + percentile_rank(d["blocks"])*0.15 + percentile_rank(d["aerial_won_pct"])*0.15).round(1)
    d["physical_score"]= (percentile_rank(d["duels_won_pct"])*0.50 + percentile_rank(d["yellow_cards"], ascending=False)*0.30 + percentile_rank(d["fouls_committed"], ascending=False)*0.20).round(1)
    d["passing_score"] = percentile_rank(d["passes_accuracy"]).round(1)
    d["overall_score"] = (d["defense_score"]*0.55 + d["physical_score"]*0.25 + d["passing_score"]*0.20).round(1)
    d["attack_score"]  = None
    return d


def calculate_goalkeeper_scores(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["defense_score"] = (percentile_rank(d["saves_pct"])*0.45 + percentile_rank(d["clean_sheets"])*0.35 + percentile_rank(d["goals_conceded"], ascending=False)*0.20).round(1)
    d["overall_score"] = d["defense_score"]
    d["attack_score"]  = None
    d["passing_score"] = percentile_rank(d["passes_accuracy"]).round(1)
    d["physical_score"]= None
    return d


def add_consistency_score(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["consistency_score"] = (percentile_rank(d["minutes_played"])*0.60 + percentile_rank(d["rating"])*0.40).round(1)
    return d


def add_position_rank(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["position_rank"] = d.groupby("position")["overall_score"].rank(method="min", ascending=False).astype(int)
    d["total_players_in_position"] = d.groupby("position")["position_rank"].transform("count")
    return d


def _safe_float(val) -> float | None:
    try:
        f = float(val)
        if f != f:
            return None
        if f == float('inf') or f == float('-inf'):
            return None
        return f
    except (TypeError, ValueError):
        return None


def save_scores(df: pd.DataFrame, season: int):
    db = SessionLocal()
    try:
        deleted = db.query(ScoutingScore).filter(ScoutingScore.season == season).delete()
        db.commit()
        print(f"  -> {deleted} scores anteriores eliminados")
        scores = []
        for _, row in df.iterrows():
            scores.append(ScoutingScore(
                player_id                 = int(row["player_id"]),
                season                    = season,
                overall_score             = _safe_float(row.get("overall_score")) or 0.0,
                attack_score              = _safe_float(row.get("attack_score")),
                defense_score             = _safe_float(row.get("defense_score")),
                passing_score             = _safe_float(row.get("passing_score")),
                physical_score            = _safe_float(row.get("physical_score")),
                consistency_score         = _safe_float(row.get("consistency_score")),
                position_rank             = int(row.get("position_rank", 0)),
                total_players_in_position = int(row.get("total_players_in_position", 0)),
                algorithm_version         = "1.0",
            ))

        db.add_all(scores)
        db.commit()
        print(f"  -> {len(scores)} scores insertados correctamente")

    except Exception as e:
        db.rollback()
        print(f"  Error guardando scores: {e}")
        raise
    finally:
        db.close()


def run_scoring(season: int, position_filter: str | None = None):
    print(f"\n{'='*55}")
    print(f"Calculando Scouting Scores - Season {season}")
    print(f"{'='*55}\n")

    print("Cargando datos desde PostgreSQL...")
    df = load_stats_dataframe(season)

    if df.empty:
        print("No hay datos. Corre primero el script de ingesta.")
        return

    all_results = []
    positions = [position_filter] if position_filter else ["attacker", "midfielder", "defender", "goalkeeper"]

    for position in positions:
        pos_df = df[df["position"] == position].copy()
        if pos_df.empty:
            print(f"  Sin jugadores para posicion: {position}")
            continue

        print(f"\nProcesando {position}s ({len(pos_df)} jugadores)...")

        if position == "attacker":
            pos_df = calculate_attacker_scores(pos_df)
        elif position == "midfielder":
            pos_df = calculate_midfielder_scores(pos_df)
        elif position == "defender":
            pos_df = calculate_defender_scores(pos_df)
        elif position == "goalkeeper":
            pos_df = calculate_goalkeeper_scores(pos_df)

        pos_df = add_consistency_score(pos_df)

        top5 = pos_df.nlargest(5, "overall_score")[["name", "team_name", "overall_score", "games_played"]]
        print(f"\n  Top 5 {position}s:")
        print(top5.to_string(index=False))

        all_results.append(pos_df)

    if not all_results:
        print("No se generaron resultados.")
        return

    final_df = pd.concat(all_results, ignore_index=True)
    final_df  = add_position_rank(final_df)

    # Elimina duplicados — jugadores que aparecen en múltiples ligas
    # Mantiene el score más alto de cada jugador
    final_df = final_df.sort_values('overall_score', ascending=False)
    final_df = final_df.drop_duplicates(subset=['player_id'], keep='first')
    final_df = final_df.reset_index(drop=True)
    final_df = add_position_rank(final_df)  # Recalcula ranks después de deduplicar

    print(f"\n💾 Guardando {len(final_df)} scores en PostgreSQL...")
    save_scores(final_df, season)

    print(f"\n{'='*55}")
    print("Scores calculados exitosamente")
    print(f"{'='*55}")

    summary = final_df.groupby("position")["overall_score"].agg(["count","mean","max","min"]).round(1)
    summary.columns = ["Jugadores", "Promedio", "Maximo", "Minimo"]
    print("\nResumen por posicion:")
    print(summary.to_string())

    print(f"\nTop 10 jugadores generales:")
    top10 = final_df.nlargest(10, "overall_score")[["name","position","team_name","overall_score","position_rank"]]
    print(top10.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--season",   type=int, default=2024)
    parser.add_argument("--position", type=str, default=None,
                        choices=["attacker","midfielder","defender","goalkeeper"])
    args = parser.parse_args()
    run_scoring(season=args.season, position_filter=args.position)