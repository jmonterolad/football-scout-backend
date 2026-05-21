from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.models import League, Team, Player, ScoutingScore
from app.schemas import LeagueOut, TeamOut

router = APIRouter(prefix="/api/leagues", tags=["Leagues"])

CURRENT_SEASON = 2024


@router.get("", response_model=list[LeagueOut])
def list_leagues(db: Session = Depends(get_db)):
    return db.query(League).filter(League.is_active == True).all()


@router.get("/{league_id}/teams", response_model=list[TeamOut])
def get_teams(league_id: int, db: Session = Depends(get_db)):
    return db.query(Team).filter(Team.league_id == league_id).all()


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/leagues/{league_id}/overview
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/{league_id}/overview")
def get_league_overview(
    league_id: int,
    season: int = CURRENT_SEASON,
    db: Session = Depends(get_db),
):
    league = (
        db.query(League)
        .filter((League.api_id == league_id) | (League.id == league_id))
        .first()
    )
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    positions = ["attacker", "midfielder", "defender", "goalkeeper"]
    position_stats = {}

    for pos in positions:
        agg = (
            db.query(
                func.count(ScoutingScore.id).label("count"),
                func.avg(ScoutingScore.overall_score).label("avg_score"),
                func.max(ScoutingScore.overall_score).label("max_score"),
                func.min(ScoutingScore.overall_score).label("min_score"),
                func.avg(ScoutingScore.attack_score).label("avg_attack"),
                func.avg(ScoutingScore.defense_score).label("avg_defense"),
                func.avg(ScoutingScore.passing_score).label("avg_passing"),
                func.avg(ScoutingScore.physical_score).label("avg_physical"),
                func.avg(ScoutingScore.consistency_score).label("avg_consistency"),
            )
            .join(Player, Player.id == ScoutingScore.player_id)
            .join(Team, Team.id == Player.team_id)
            .filter(Team.league_id == league.id)
            .filter(ScoutingScore.season == season)
            .filter(Player.position == pos)
            .first()
        )

        if not agg or not agg.count:
            continue

        ranges = [
            (0, 40, "0-40"),
            (40, 50, "40-50"),
            (50, 60, "50-60"),
            (60, 70, "60-70"),
            (70, 80, "70-80"),
            (80, 101, "80+"),
        ]
        distribution = []
        for low, high, label in ranges:
            n = (
                db.query(func.count(ScoutingScore.id))
                .join(Player, Player.id == ScoutingScore.player_id)
                .join(Team, Team.id == Player.team_id)
                .filter(Team.league_id == league.id)
                .filter(ScoutingScore.season == season)
                .filter(Player.position == pos)
                .filter(ScoutingScore.overall_score >= low)
                .filter(ScoutingScore.overall_score < high)
                .scalar()
                or 0
            )
            distribution.append({"range": label, "count": n})

        top = (
            db.query(Player)
            .options(joinedload(Player.team), joinedload(Player.scouting_scores))
            .join(Player.scouting_scores)
            .join(Player.team)
            .filter(Team.league_id == league.id)
            .filter(ScoutingScore.season == season)
            .filter(Player.position == pos)
            .filter(ScoutingScore.overall_score.isnot(None))
            .order_by(ScoutingScore.overall_score.desc())
            .first()
        )

        top_score = None
        if top:
            top_score = next(
                (s.overall_score for s in top.scouting_scores if s.season == season),
                None,
            )

        def r(val):
            return round(float(val), 1) if val is not None else None

        position_stats[pos] = {
            "count": agg.count,
            "avg_score": r(agg.avg_score),
            "max_score": r(agg.max_score),
            "min_score": r(agg.min_score),
            "avg_attack": r(agg.avg_attack),
            "avg_defense": r(agg.avg_defense),
            "avg_passing": r(agg.avg_passing),
            "avg_physical": r(agg.avg_physical),
            "avg_consistency": r(agg.avg_consistency),
            "distribution": distribution,
            "top_player": {
                "id": top.id,
                "name": top.name,
                "photo_url": top.photo_url,
                "overall_score": top_score,
            }
            if top
            else None,
        }

    return {
        "league": {"id": league.id, "name": league.name, "country": league.country},
        "season": season,
        "position_stats": position_stats,
    }
