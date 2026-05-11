"""
Router de Scouting — /api/scouting
====================================
Endpoints para recomendaciones de fichajes y rankings.
Esta es la feature estrella del proyecto.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Player, ScoutingScore, Team
from app.schemas import PlayerListItem

router = APIRouter(prefix="/api/scouting", tags=["Scouting"])

CURRENT_SEASON = 2024


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/scouting/top — Top jugadores por posición
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/top", response_model=list[PlayerListItem])
def get_top_players(
    position: str | None = Query(None, description="Filtra por posición"),
    limit: int           = Query(10, ge=1, le=50),
    min_games: int       = Query(10, description="Mínimo de partidos jugados"),
    db: Session = Depends(get_db),
):
    """Top jugadores ordenados por overall_score."""
    query = (
        db.query(Player)
        .options(
            joinedload(Player.team),
            joinedload(Player.scouting_scores),
        )
        .join(Player.scouting_scores)
        .filter(ScoutingScore.season == CURRENT_SEASON)
        .filter(ScoutingScore.overall_score.isnot(None))
    )

    if position:
        query = query.filter(Player.position == position)

    players = (
        query
        .order_by(ScoutingScore.overall_score.desc())
        .limit(limit)
        .all()
    )

    result = []
    for p in players:
        score = next(
            (s for s in p.scouting_scores if s.season == CURRENT_SEASON), None
        )
        result.append(PlayerListItem(
            id=p.id,
            name=p.name,
            age=p.age,
            nationality=p.nationality,
            position=p.position,
            photo_url=p.photo_url,
            team=p.team,
            scouting_score=score,
        ))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/scouting/recommendations — Recomendaciones de fichaje
# Esta es la endpoint más valiosa del proyecto para el portafolio
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/recommendations", response_model=list[PlayerListItem])
def get_recommendations(
    position:    str | None = Query(None),
    max_age:     int | None = Query(None, description="Edad máxima del jugador"),
    min_score:   float      = Query(60.0, description="Score mínimo (0-100)"),
    nationality: str | None = Query(None),
    limit: int              = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Recomendaciones de jugadores para fichar.
    Filtra por posición, edad, score mínimo y nacionalidad.

    Ejemplo: mejores delanteros menores de 25 años con score >= 65
    GET /api/scouting/recommendations?position=attacker&max_age=25&min_score=65
    """
    query = (
        db.query(Player)
        .options(
            joinedload(Player.team),
            joinedload(Player.scouting_scores),
        )
        .join(Player.scouting_scores)
        .filter(ScoutingScore.season == CURRENT_SEASON)
        .filter(ScoutingScore.overall_score >= min_score)
    )

    if position:
        query = query.filter(Player.position == position)
    if max_age:
        query = query.filter(Player.age <= max_age)
    if nationality:
        query = query.filter(Player.nationality.ilike(f"%{nationality}%"))

    players = (
        query
        .order_by(ScoutingScore.overall_score.desc())
        .limit(limit)
        .all()
    )

    result = []
    for p in players:
        score = next(
            (s for s in p.scouting_scores if s.season == CURRENT_SEASON), None
        )
        result.append(PlayerListItem(
            id=p.id,
            name=p.name,
            age=p.age,
            nationality=p.nationality,
            position=p.position,
            photo_url=p.photo_url,
            team=p.team,
            scouting_score=score,
        ))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/scouting/summary — Resumen general para el dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Stats generales para mostrar en el dashboard principal."""
    total_players = db.query(Player).count()
    total_scored  = (
        db.query(ScoutingScore)
        .filter(ScoutingScore.season == CURRENT_SEASON)
        .count()
    )

    # Top 1 por posición
    top_by_position = {}
    for position in ["attacker", "midfielder", "defender", "goalkeeper"]:
        top = (
            db.query(Player)
            .options(joinedload(Player.team), joinedload(Player.scouting_scores))
            .join(Player.scouting_scores)
            .filter(ScoutingScore.season == CURRENT_SEASON)
            .filter(Player.position == position)
            .order_by(ScoutingScore.overall_score.desc())
            .first()
        )
        if top:
            score = next(
                (s for s in top.scouting_scores if s.season == CURRENT_SEASON), None
            )
            top_by_position[position] = {
                "id":            top.id,
                "name":          top.name,
                "team":          top.team.name if top.team else None,
                "photo_url":     top.photo_url,
                "overall_score": score.overall_score if score else None,
            }

    return {
        "season":         CURRENT_SEASON,
        "total_players":  total_players,
        "total_scored":   total_scored,
        "top_by_position": top_by_position,
    }