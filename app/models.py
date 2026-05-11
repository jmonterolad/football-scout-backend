"""
Modelos de base de datos — Football Scout Analytics
====================================================
5 tablas core que representan toda la data del proyecto:

  leagues → teams → players → player_stats
                            ↘ scouting_scores
"""

from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean,
    ForeignKey, DateTime, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# ─── LEAGUES ─────────────────────────────────────────────────────────────────

class League(Base):
    """
    Ligas de fútbol.
    Ejemplos: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1
    """
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ID de API-Football (para sincronizar data)
    api_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    season: Mapped[int] = mapped_column(Integer, nullable=False)  # Ej: 2024
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relaciones
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="league")

    def __repr__(self):
        return f"<League {self.name} ({self.country}) - {self.season}>"


# ─── TEAMS ───────────────────────────────────────────────────────────────────

class Team(Base):
    """
    Equipos de fútbol asociados a una liga.
    """
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    api_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(10))  # Ej: "MCI", "BAR"
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    founded: Mapped[int | None] = mapped_column(Integer)  # Año de fundación
    stadium: Mapped[str | None] = mapped_column(String(200))

    # FK a liga
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relaciones
    league: Mapped["League"] = relationship("League", back_populates="teams")
    players: Mapped[list["Player"]] = relationship("Player", back_populates="team")

    def __repr__(self):
        return f"<Team {self.name}>"


# ─── PLAYERS ─────────────────────────────────────────────────────────────────

class Player(Base):
    """
    Jugadores de fútbol.
    Datos base del jugador (no cambian mucho entre temporadas).
    """
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    api_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))

    age: Mapped[int | None] = mapped_column(Integer)
    birth_date: Mapped[str | None] = mapped_column(String(20))  # "1998-05-15"
    nationality: Mapped[str | None] = mapped_column(String(100))
    height: Mapped[str | None] = mapped_column(String(20))  # "180 cm"
    weight: Mapped[str | None] = mapped_column(String(20))  # "75 kg"
    photo_url: Mapped[str | None] = mapped_column(String(500))

    # Posición: goalkeeper, defender, midfielder, attacker
    position: Mapped[str | None] = mapped_column(String(50), index=True)

    # Valor de mercado en millones de euros (para mostrar en UI)
    market_value: Mapped[float | None] = mapped_column(Float)

    # FK al equipo actual
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relaciones
    team: Mapped["Team | None"] = relationship("Team", back_populates="players")
    stats: Mapped[list["PlayerStats"]] = relationship(
        "PlayerStats", back_populates="player", cascade="all, delete-orphan"
    )
    scouting_scores: Mapped[list["ScoutingScore"]] = relationship(
        "ScoutingScore", back_populates="player", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Player {self.name} | {self.position}>"


# ─── PLAYER STATS ─────────────────────────────────────────────────────────────

class PlayerStats(Base):
    """
    Estadísticas del jugador por temporada.
    Esta tabla es el corazón del análisis — aquí viven todos los números.

    Las métricas están separadas por categoría:
      - Generales (partidos, minutos)
      - Ataque (goles, xG, disparos)
      - Pases (asistencias, precisión, xA)
      - Defensa (tackles, intercepciones)
      - Duelos (disputas ganadas)
      - Físico (tarjetas, faltas)
    """
    __tablename__ = "player_stats"

    # Un jugador solo tiene UN registro por temporada+liga
    __table_args__ = (
        UniqueConstraint("player_id", "season", "league_id", name="uq_player_season_league"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # FKs
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)  # Ej: 2024

    # ── Generales ──────────────────────────────────────────────
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    games_started: Mapped[int] = mapped_column(Integer, default=0)
    minutes_played: Mapped[int] = mapped_column(Integer, default=0)
    # Minutos por 90 — base para todas las métricas "per 90"
    minutes_per90: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[float | None] = mapped_column(Float)  # Rating promedio (0-10)

    # ── Ataque ─────────────────────────────────────────────────
    goals: Mapped[int] = mapped_column(Integer, default=0)
    goals_per90: Mapped[float | None] = mapped_column(Float)
    xg: Mapped[float | None] = mapped_column(Float)         # Goles esperados total
    xg_per90: Mapped[float | None] = mapped_column(Float)   # xG por 90 minutos
    shots_total: Mapped[int] = mapped_column(Integer, default=0)
    shots_on_target: Mapped[int] = mapped_column(Integer, default=0)
    shot_accuracy: Mapped[float | None] = mapped_column(Float)  # % disparos al arco

    # ── Pases y creación ───────────────────────────────────────
    assists: Mapped[int] = mapped_column(Integer, default=0)
    assists_per90: Mapped[float | None] = mapped_column(Float)
    xa: Mapped[float | None] = mapped_column(Float)          # Asistencias esperadas
    xa_per90: Mapped[float | None] = mapped_column(Float)
    passes_total: Mapped[int] = mapped_column(Integer, default=0)
    passes_accuracy: Mapped[float | None] = mapped_column(Float)  # % pases completados
    key_passes: Mapped[int] = mapped_column(Integer, default=0)   # Pases que generan remate
    key_passes_per90: Mapped[float | None] = mapped_column(Float)

    # ── Defensa ────────────────────────────────────────────────
    tackles_total: Mapped[int] = mapped_column(Integer, default=0)
    tackles_success: Mapped[float | None] = mapped_column(Float)  # % tackles exitosos
    interceptions: Mapped[int] = mapped_column(Integer, default=0)
    blocks: Mapped[int] = mapped_column(Integer, default=0)
    clearances: Mapped[int] = mapped_column(Integer, default=0)

    # ── Duelos ─────────────────────────────────────────────────
    duels_total: Mapped[int] = mapped_column(Integer, default=0)
    duels_won: Mapped[int] = mapped_column(Integer, default=0)
    duels_won_pct: Mapped[float | None] = mapped_column(Float)     # % duelos ganados
    aerial_total: Mapped[int] = mapped_column(Integer, default=0)
    aerial_won: Mapped[int] = mapped_column(Integer, default=0)
    aerial_won_pct: Mapped[float | None] = mapped_column(Float)    # % duelos aéreos ganados

    # ── Dribbling ──────────────────────────────────────────────
    dribbles_attempts: Mapped[int] = mapped_column(Integer, default=0)
    dribbles_success: Mapped[int] = mapped_column(Integer, default=0)
    dribbles_success_pct: Mapped[float | None] = mapped_column(Float)

    # ── Físico / disciplina ────────────────────────────────────
    fouls_drawn: Mapped[int] = mapped_column(Integer, default=0)   # Faltas recibidas
    fouls_committed: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, default=0)

    # ── Solo porteros ──────────────────────────────────────────
    goals_conceded: Mapped[int | None] = mapped_column(Integer)
    saves: Mapped[int | None] = mapped_column(Integer)
    saves_pct: Mapped[float | None] = mapped_column(Float)
    clean_sheets: Mapped[int | None] = mapped_column(Integer)
    penalties_saved: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relaciones
    player: Mapped["Player"] = relationship("Player", back_populates="stats")
    league: Mapped["League"] = relationship("League")

    def __repr__(self):
        return f"<PlayerStats player_id={self.player_id} season={self.season}>"


# ─── SCOUTING SCORES ──────────────────────────────────────────────────────────

class ScoutingScore(Base):
    """
    Puntuaciones calculadas por nuestro algoritmo de scouting.

    Este es el valor único del proyecto:
    tomamos las stats brutas y las convertimos en scores
    comparables entre jugadores de la misma posición.

    Scores van de 0 a 100.
    """
    __tablename__ = "scouting_scores"

    __table_args__ = (
        UniqueConstraint("player_id", "season", name="uq_score_player_season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Score general y por categoría (0-100) ────────────────
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    attack_score: Mapped[float | None] = mapped_column(Float)
    defense_score: Mapped[float | None] = mapped_column(Float)
    passing_score: Mapped[float | None] = mapped_column(Float)
    physical_score: Mapped[float | None] = mapped_column(Float)
    consistency_score: Mapped[float | None] = mapped_column(Float)

    # ── Ranking dentro de su posición en esa liga ─────────────
    # Ej: rank 3 significa que es el 3er mejor delantero de la liga
    position_rank: Mapped[int | None] = mapped_column(Integer)
    total_players_in_position: Mapped[int | None] = mapped_column(Integer)

    # ── Metadata del cálculo ──────────────────────────────────
    # Para saber cuándo se calculó y con qué versión del algoritmo
    algorithm_version: Mapped[str] = mapped_column(String(20), default="1.0")
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relaciones
    player: Mapped["Player"] = relationship("Player", back_populates="scouting_scores")

    def __repr__(self):
        return (
            f"<ScoutingScore player_id={self.player_id} "
            f"overall={self.overall_score:.1f} season={self.season}>"
        )
