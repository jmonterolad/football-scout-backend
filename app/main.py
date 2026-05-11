from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import engine, Base
from app.routers import players, scouting, leagues

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Football Scout Analytics API",
    description="API para análisis de jugadores de fútbol y recomendaciones de fichajes",
    version="1.0.0",
)

# CORS debe registrarse ANTES que cualquier otro middleware o handler
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handler global de errores — asegura que los 500 también tengan CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "http://localhost:5173"},
    )

# ── Registra todos los routers ────────────────────────────────────────────────
app.include_router(players.router)
app.include_router(scouting.router)
app.include_router(leagues.router)


@app.get("/")
def root():
    return {"message": "Football Scout Analytics API", "docs": "/docs", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}