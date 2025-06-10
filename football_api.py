# football_api.py
"""
Wrapper para consulta de datos de jugadores de fútbol vía API-Sports.
Gestiona búsqueda de player_id con múltiples estrategias, cache local,
y recuperación de estadísticas, traspasos, trofeos, lesiones, etc.
"""

import json
import os
import time
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

import certifi
import requests
from dotenv import load_dotenv
from requests.exceptions import SSLError

# ── Configuración y constantes ───────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("APIFOOTBALL_KEY", "") or os.getenv("APISPORTS_KEY", "")
if not API_KEY:
    raise RuntimeError("Falta APIFOOTBALL_KEY o APISPORTS_KEY en .env")

HEADERS    = {"x-apisports-key": API_KEY}
BASE_URL   = "https://v3.football.api-sports.io"
CACHE_FILE = Path(__file__).with_name("player_cache.json")

LEAGUES  = [39, 78, 61, 135, 140, 307]     # Ligas principales
SEASONS  = [2024, 2023, 2022, 2021, 2020]  

if CACHE_FILE.exists():
    _CACHE: Dict[str, int] = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
else:
    _CACHE = {}

def _save_cache() -> None:
    CACHE_FILE.write_text(
        json.dumps(_CACHE, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

def _strip(text: str) -> str:
    """Normalize y quita acentos para comparaciones."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()

def _get(path: str, **params):
    url = f"{BASE_URL}/{path}"
    for _ in range(2):
        try:
            r = requests.get(url,
                             headers=HEADERS,
                             params=params,
                             timeout=15,
                             verify=certifi.where())
        except SSLError:
            r = requests.get(url,
                             headers=HEADERS,
                             params=params,
                             timeout=15,
                             verify=False)
        if r.ok:
            return r.json()["response"]
        time.sleep(1)
    r.raise_for_status()


def _resolve_id(name: str) -> tuple[int, dict]:
    """
    Busca un jugador por varios métodos y, si todo falla con nombre completo,
    reintenta sólo con el primer nombre (antes de levantar LookupError).
    """
    q_full = ''.join(c for c in unicodedata.normalize("NFD", name)
                     if unicodedata.category(c)!='Mn').lower()

    res = _get("players", search=q_full) or []
    if res:
        return res[0]["player"]["id"], res[0]
    
    for lg in LEAGUES:
        for yr in SEASONS:
            res = _get("players", search=q_full, league=lg, season=yr) or []
            if res:
                return res[0]["player"]["id"], res[0]

    for lg in LEAGUES:
        res = _get("players", search=q_full, league=lg) or []
        if res:
            return res[0]["player"]["id"], res[0]

    for yr in SEASONS:
        res = _get("players", search=q_full, season=yr) or []
        if res:
            return res[0]["player"]["id"], res[0]

    if " " in name:
        tokens = name.split()
        try:
            return _resolve_id(tokens[0])
        except LookupError:
            return _resolve_id(tokens[-1])

    raise LookupError(f"No se encontró «{name}» en API-Football")

@lru_cache(maxsize=256)
def player_info(name: str) -> Dict[str, Any]:
    """
    Devuelve un dict con:
      basic: perfil básico
      seasons: lista de años con estadísticas
      stats: map temporada→statistics
      transfers, trophies, injuries, sidelined
    """
    key = _strip(name)

    if key in _CACHE:
        pid = _CACHE[key]
        resp = _get("players", id=pid) or []
        first_block = resp[0] if resp else {}
    else:
        pid, first_block = _resolve_id(name)
        _CACHE[key] = pid
        _save_cache()


    basic = None
    seasons_found: List[Any] = []
    stats_map: Dict[Any, Any] = {}
    for yr in SEASONS:
        blk = _get("players", id=pid, season=yr) or []
        if blk:
            seasons_found.append(yr)
            stats_map[yr] = blk[0]["statistics"]
            if basic is None:
                basic = blk[0]

    if basic is None:
        blk0 = _get("players", id=pid) or []
        if blk0:
            basic = blk0[0]
            seasons_found.append("N/A")
            stats_map["N/A"] = blk0[0]["statistics"]
        elif first_block:
            basic = first_block
        else:
            raise LookupError("No se pudieron obtener estadísticas")

    return {
        "basic":     basic,
        "seasons":   seasons_found,
        "stats":     stats_map,
        "transfers": _get("transfers", player=pid),
        "trophies":  _get("trophies",  player=pid),
        "injuries":  _get("injuries",  player=pid),
        "sidelined": _get("sidelined", player=pid),
    }
