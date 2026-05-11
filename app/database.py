from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings


# ─── Configuración desde .env ────────────────────────────────────────────────

class Settings(BaseSettings):
    DATABASE_URL: str
    API_FOOTBALL_KEY: str
    API_FOOTBALL_BASE_URL: str = "https://v3.football.api-sports.io"
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()


# ─── Engine y sesión ─────────────────────────────────────────────────────────

engine = create_engine(
    settings.DATABASE_URL,
    # Pool de conexiones: cuántas conexiones simultáneas mantener abiertas
    pool_size=5,
    max_overflow=10,
    # Muestra las queries SQL en consola (útil en desarrollo)
    echo=settings.APP_ENV == "development",
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ─── Base para todos los modelos ─────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─── Dependency para FastAPI ──────────────────────────────────────────────────
# Se usará en cada endpoint como: db: Session = Depends(get_db)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
