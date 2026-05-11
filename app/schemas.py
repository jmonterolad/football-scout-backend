"""
Schemas de Pydantic — Football Scout Analytics
===============================================
Definen la forma exacta de los datos que entran y salen de la API.
Pydantic valida automáticamente tipos y formatos.

Separamos Input (requests) de Output (responses) porque
a veces necesitamos mostrar más o menos campos según el contexto.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# LEAGUE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class LeagueOut(BaseModel):
    id: int
    api_id: int
    name: str
    country: str
    logo_url: Optional[str]
    season: int

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# TEAM SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class TeamOut(BaseModel):
    id: int
    name: str
    short_name: Optional[str]
    country: str
    logo_url: Optional[str]
    stadium: Optional[str]
    league_id: int

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# SCOUTING SCORE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ScoutingScoreOut(BaseModel):
    overall_score: float
    attack_score: Optional[float]
    defense_score: Optional[float]
    passing_score: Optional[float]
    physical_score: Optional[float]
    consistency_score: Optional[float]
    position_rank: Optional[int]
    total_players_in_position: Optional[int]
    algorithm_version: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# PLAYER STATS SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class PlayerStatsOut(BaseModel):
    season: int
    games_played: Optional[int] = 0
    games_started: Optional[int] = 0
    minutes_played: Optional[int] = 0
    rating: Optional[float] = None

    # Ataque
    goals: Optional[int] = 0
    goals_per90: Optional[float] = None
    xg: Optional[float] = None
    xg_per90: Optional[float] = None
    shots_total: Optional[int] = 0
    shot_accuracy: Optional[float] = None

    # Pases
    assists: Optional[int] = 0
    assists_per90: Optional[float] = None
    xa: Optional[float] = None
    passes_accuracy: Optional[float] = None
    key_passes: Optional[int] = 0
    key_passes_per90: Optional[float] = None

    # Defensa
    tackles_total: Optional[int] = 0
    interceptions: Optional[int] = 0
    blocks: Optional[int] = 0

    # Duelos
    duels_won_pct: Optional[float] = None
    aerial_won_pct: Optional[float] = None

    # Dribbling
    dribbles_success_pct: Optional[float] = None

    # Disciplina
    yellow_cards: Optional[int] = 0
    red_cards: Optional[int] = 0

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# PLAYER SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class PlayerListItem(BaseModel):
    """Schema liviano para listas — no trae todas las stats."""
    id: int
    name: str
    age: Optional[int]
    nationality: Optional[str]
    position: Optional[str]
    photo_url: Optional[str]
    team: Optional[TeamOut]
    scouting_score: Optional[ScoutingScoreOut] = None

    model_config = {"from_attributes": True}


class PlayerDetail(BaseModel):
    """Schema completo para el perfil de un jugador."""
    id: int
    api_id: int
    name: str
    first_name: Optional[str]
    last_name: Optional[str]
    age: Optional[int]
    birth_date: Optional[str]
    nationality: Optional[str]
    height: Optional[str]
    weight: Optional[str]
    photo_url: Optional[str]
    position: Optional[str]
    market_value: Optional[float]
    team: Optional[TeamOut]
    stats: list[PlayerStatsOut] = []
    scouting_score: Optional[ScoutingScoreOut] = None

    model_config = {"from_attributes": True}


class RadarData(BaseModel):
    """
    Datos formateados para el radar chart del frontend.
    Cada métrica ya está normalizada a 0-100.
    """
    player_id: int
    player_name: str
    position: str
    team_name: str
    metrics: dict[str, float] = Field(
        description="Diccionario métrica → valor (0-100)"
    )


class CompareItem(BaseModel):
    """Un jugador dentro de una comparación."""
    player_id: int
    player_name: str
    position: str
    team_name: str
    photo_url: Optional[str]
    overall_score: float
    stats: PlayerStatsOut
    scouting_score: ScoutingScoreOut


# ─────────────────────────────────────────────────────────────────────────────
# PAGINATION SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class PaginatedPlayers(BaseModel):
    """Respuesta paginada para el listado de jugadores."""
    total: int
    page: int
    per_page: int
    pages: int
    data: list[PlayerListItem]