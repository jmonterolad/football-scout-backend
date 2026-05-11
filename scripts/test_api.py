"""
Test rápido para verificar que tu API key funciona
CORRE ESTO PRIMERO antes del script de ingesta completo.

Uso: python scripts/test_api.py
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api_client import APIFootballClient
from app.database import settings

def test_connection():
    print("\n🔍 Verificando configuración...")
    print(f"   API Key: {'✅ configurada' if settings.API_FOOTBALL_KEY else '❌ FALTA en .env'}")
    print(f"   DB URL:  {'✅ configurada' if settings.DATABASE_URL else '❌ FALTA en .env'}")

    if not settings.API_FOOTBALL_KEY:
        print("\n❌ Agrega tu API_FOOTBALL_KEY al archivo .env")
        return

    print("\n📡 Probando conexión a API-Football...")
    client = APIFootballClient()

    # Trae info de la Premier League 2024 — solo 1 request
    data = client.get_league(league_id=39, season=2024)

    if data:
        league = data.get("league", {})
        country = data.get("country", {})
        print(f"\n✅ ¡Conexión exitosa!")
        print(f"   Liga encontrada: {league.get('name')}")
        print(f"   País: {country.get('name')}")
        print(f"   Logo: {league.get('logo')}")
        print(f"\n🎯 Tu API key funciona. Puedes correr el script de ingesta.")
    else:
        print("\n❌ No se recibieron datos. Verifica tu API key.")

    # Muestra cuántos requests te quedan
    print("\n💡 Recuerda: el plan gratuito tiene 100 requests/día")
    print("   La ingesta completa (5 ligas) usa ~300-400 requests")
    print("   Empieza con UNA liga: python -m scripts.ingest_data --season 2024 --league 39")

if __name__ == "__main__":
    test_connection()
