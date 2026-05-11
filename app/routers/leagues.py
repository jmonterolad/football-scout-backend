from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import League, Team
from app.schemas import LeagueOut, TeamOut

router = APIRouter(prefix="/api/leagues", tags=["Leagues"])


@router.get("", response_model=list[LeagueOut])
def list_leagues(db: Session = Depends(get_db)):
    return db.query(League).filter(League.is_active == True).all()


@router.get("/{league_id}/teams", response_model=list[TeamOut])
def get_teams(league_id: int, db: Session = Depends(get_db)):
    return db.query(Team).filter(Team.league_id == league_id).all()