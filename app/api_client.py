"""
Cliente para API-Football
=========================
Maneja todas las llamadas a la API externa.
Plan gratuito: 100 requests/día — úsalos con cuidado.
"""

import httpx
import time
from app.database import settings


class APIFootballClient:

    def __init__(self):
        self.base_url = settings.API_FOOTBALL_BASE_URL
        self.headers = {
            "x-apisports-key": settings.API_FOOTBALL_KEY
        }
        # Espera entre requests para no superar el rate limit
        self.delay_seconds = 3.5

    def _get(self, endpoint: str, params: dict = {}) -> dict:
        url = f"{self.base_url}/{endpoint}"
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=self.headers, params=params)

            if response.status_code == 429:
                print("\n⚠️  Rate limit alcanzado. Esperando 60 segundos...")
                time.sleep(60)
                # Reintenta una vez
                response = client.get(url, headers=self.headers, params=params)

            response.raise_for_status()
            time.sleep(self.delay_seconds)
            return response.json()

    # ── Ligas ──────────────────────────────────────────────────────────────

    def get_league(self, league_id: int, season: int) -> dict:
        """Trae info de una liga específica."""
        data = self._get("leagues", {"id": league_id, "season": season})
        if data["results"] > 0:
            return data["response"][0]
        return {}

    # ── Equipos ────────────────────────────────────────────────────────────

    def get_teams_by_league(self, league_id: int, season: int) -> list:
        """Trae todos los equipos de una liga en una temporada."""
        data = self._get("teams", {"league": league_id, "season": season})
        return data.get("response", [])

    # ── Jugadores ──────────────────────────────────────────────────────────

    def get_players_by_team(self, team_id: int, season: int) -> list:
        """
        Trae jugadores de un equipo con sus stats.
        La API pagina los resultados (20 por página).
        """
        all_players = []
        page = 1

        while True:
            data = self._get("players", {
                "team": team_id,
                "season": season,
                "page": page
            })

            players = data.get("response", [])
            if not players:
                break

            all_players.extend(players)

            # Revisa si hay más páginas
            total_pages = data.get("paging", {}).get("total", 1)
            if page >= total_pages:
                break

            page += 1

        return all_players
