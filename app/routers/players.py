"""
Router de Jugadores — /api/players
===================================
Todos los endpoints relacionados con jugadores.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.database import get_db
from app.models import Player, PlayerStats, ScoutingScore, Team
from app.schemas import PlayerDetail, PlayerListItem, PaginatedPlayers, RadarData, CompareItem

router = APIRouter(prefix="/api/players", tags=["Players"])

CURRENT_SEASON = 2024


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/players — Listado con filtros y paginación
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedPlayers)
def list_players(
    # Filtros
    position:   str  | None = Query(None, description="attacker | midfielder | defender | goalkeeper"),
    team_id:    int  | None = Query(None),
    league_id:  int  | None = Query(None),
    nationality:str  | None = Query(None),
    min_score:  float| None = Query(None, description="Score mínimo (0-100)"),
    search:     str  | None = Query(None, description="Buscar por nombre"),
    # Paginación
    page:     int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Player)
        .options(
            joinedload(Player.team),
            joinedload(Player.scouting_scores),
        )
        .join(Player.team, isouter=True)
    )

    # Aplica filtros
    if position:
        query = query.filter(Player.position == position)
    if team_id:
        query = query.filter(Player.team_id == team_id)
    if league_id:
        query = query.join(Player.team).filter(Team.league_id == league_id)
    if nationality:
        query = query.filter(Player.nationality.ilike(f"%{nationality}%"))
    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))
    if min_score:
        query = (
            query
            .join(Player.scouting_scores)
            .filter(ScoutingScore.overall_score >= min_score)
            .filter(ScoutingScore.season == CURRENT_SEASON)
        )

    total = query.count()
    players = query.offset((page - 1) * per_page).limit(per_page).all()

    # Agrega el scouting_score de la temporada actual a cada jugador
    result = []
    for p in players:
        current_score = next(
            (s for s in p.scouting_scores if s.season == CURRENT_SEASON), None
        )
        item = PlayerListItem(
            id=p.id,
            name=p.name,
            age=p.age,
            nationality=p.nationality,
            position=p.position,
            photo_url=p.photo_url,
            team=p.team,
            scouting_score=current_score,
        )
        result.append(item)

    return PaginatedPlayers(
        total=total,
        page=page,
        per_page=per_page,
        pages=-(-total // per_page),  # Ceiling division
        data=result,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/players/{id} — Perfil completo del jugador
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{player_id}", response_model=PlayerDetail)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = (
        db.query(Player)
        .options(
            joinedload(Player.team).joinedload(Team.league),
            joinedload(Player.stats),
            joinedload(Player.scouting_scores),
        )
        .filter(Player.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    current_score = next(
        (s for s in player.scouting_scores if s.season == CURRENT_SEASON), None
    )

    return PlayerDetail(
        id=player.id,
        api_id=player.api_id,
        name=player.name,
        first_name=player.first_name,
        last_name=player.last_name,
        age=player.age,
        birth_date=player.birth_date,
        nationality=player.nationality,
        height=player.height,
        weight=player.weight,
        photo_url=player.photo_url,
        position=player.position,
        market_value=player.market_value,
        team=player.team,
        stats=player.stats,
        scouting_score=current_score,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/players/{id}/radar — Datos para el radar chart
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{player_id}/radar", response_model=RadarData)
def get_radar_data(player_id: int, db: Session = Depends(get_db)):
    """
    Retorna métricas normalizadas (0-100) para el radar chart.
    Los scores ya están calculados como percentiles — perfectos para radar.
    """
    player = (
        db.query(Player)
        .options(joinedload(Player.team), joinedload(Player.scouting_scores))
        .filter(Player.id == player_id)
        .first()
    )
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    score = next(
        (s for s in player.scouting_scores if s.season == CURRENT_SEASON), None
    )
    if not score:
        raise HTTPException(status_code=404, detail="No scouting score found for this player")

    # Métricas del radar según posición
    if player.position == "attacker":
        metrics = {
            "Goles":        score.attack_score or 0,
            "Asistencias":  score.passing_score or 0,
            "Dribbling":    score.physical_score or 0,
            "Consistencia": score.consistency_score or 0,
            "Overall":      score.overall_score,
        }
    elif player.position == "midfielder":
        metrics = {
            "Pases":        score.passing_score or 0,
            "Ataque":       score.attack_score or 0,
            "Defensa":      score.defense_score or 0,
            "Consistencia": score.consistency_score or 0,
            "Overall":      score.overall_score,
        }
    elif player.position == "defender":
        metrics = {
            "Defensa":      score.defense_score or 0,
            "Físico":       score.physical_score or 0,
            "Pases":        score.passing_score or 0,
            "Consistencia": score.consistency_score or 0,
            "Overall":      score.overall_score,
        }
    else:  # goalkeeper
        metrics = {
            "Paradas":      score.defense_score or 0,
            "Pases":        score.passing_score or 0,
            "Consistencia": score.consistency_score or 0,
            "Overall":      score.overall_score,
        }

    return RadarData(
        player_id=player.id,
        player_name=player.name,
        position=player.position or "",
        team_name=player.team.name if player.team else "",
        metrics=metrics,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/players/compare — Comparar hasta 3 jugadores
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/compare/players", response_model=list[CompareItem])
def compare_players(
    ids: str = Query(..., description="IDs separados por coma. Ej: 1,2,3"),
    db: Session = Depends(get_db),
):
    id_list = [int(i.strip()) for i in ids.split(",")][:3]  # Máximo 3

    players = (
        db.query(Player)
        .options(
            joinedload(Player.team),
            joinedload(Player.stats),
            joinedload(Player.scouting_scores),
        )
        .filter(Player.id.in_(id_list))
        .all()
    )

    result = []
    for p in players:
        score = next(
            (s for s in p.scouting_scores if s.season == CURRENT_SEASON), None
        )
        current_stats = next(
            (st for st in p.stats if st.season == CURRENT_SEASON), None
        )

        if not score or not current_stats:
            continue

        result.append(CompareItem(
            player_id=p.id,
            player_name=p.name,
            position=p.position or "",
            team_name=p.team.name if p.team else "",
            photo_url=p.photo_url,
            overall_score=score.overall_score,
            stats=current_stats,
            scouting_score=score,
        ))

    return result