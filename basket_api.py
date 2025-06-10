# basket_api.py
"""
Wrapper para estadísticas de jugadores NBA v2.3.
Provee player_info(player_id, *, season, team_id, game_id) → dict.
"""
import os
import re
import sys
import json
from typing import Any, Dict, Optional, Union
import requests
from dotenv import load_dotenv

# ── Configuración ─────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("APISPORTS_KEY", "") or os.getenv("API_SPORTS_KEY", "")
if not API_KEY:
    raise RuntimeError("Falta APISPORTS_KEY en .env para NBA")

BASE_URL = "https://v2.nba.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
    "accept": "application/json",
}


class NBAApiError(RuntimeError):
    pass


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _resolve_player_id(name: str, season: Optional[int] = None) -> int:
    """
    Busca player_id por nombre, probando con season y sin ella.
    Toma la primera coincidencia.
    """
    params = {"search": name}
    if season:
        params["season"] = season

    url = f"{BASE_URL}/players"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("response", [])

    if not data:
        # second attempt without season
        resp = requests.get(url, headers=HEADERS, params={"search": name}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("response", [])

    if not data:
        raise NBAApiError(f"No encontrado jugador '{name}'")

    return data[0]["player"]["id"]


def player_info(
    player_id: Union[int, str],
    *,
    season: Optional[int] = None,
    team_id: Optional[int] = None,
    game_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Devuelve estadísticas de /players/statistics.
    • player_id: int o str (si es nombre, se resuelve internamente).
    • season, team_id, game_id son opcionales según necesidad.
    """
    # si pasaron nombre en lugar de ID
    if isinstance(player_id, str) and not player_id.isdigit():
        player_id = _resolve_player_id(player_id, season)

    params: Dict[str, Any] = {
        "id":     int(player_id),
        "season": season,
        "team":   team_id,
        "game":   game_id,
    }
    # limpia None
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{BASE_URL}/players/statistics"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()
