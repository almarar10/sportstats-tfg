# mma_api.py
"""
Wrapper para consulta de peleadores MMA vía API-Sports.
Provee fighter_info(name_or_id) → dict JSON de /fighters.
"""
import os
from typing import Any, Dict, Union
import requests
from dotenv import load_dotenv

# ── Configuración ─────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("APISPORTS_KEY", "")
if not API_KEY:
    raise RuntimeError("Falta APISPORTS_KEY en .env para MMA")

BASE_URL = "https://v1.mma.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
    "accept": "application/json",
}


class MMAApiError(RuntimeError):
    pass


def fighter_info(name_or_id: Union[str, int]) -> Dict[str, Any]:
    """
    Devuelve datos de /fighters.
    • Si name_or_id es int → busca por id.
    • Si es str           → busca con ?search=name.
    """
    params: Dict[str, Any]
    if isinstance(name_or_id, int):
        params = {"id": name_or_id}
    else:
        params = {"search": name_or_id}

    url = f"{BASE_URL}/fighters"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    if resp.status_code != 200:
        raise MMAApiError(f"HTTP {resp.status_code} en /fighters")
    data = resp.json()
    if not data.get("results"):
        raise MMAApiError(f"No encontrado peleador '{name_or_id}'")
    return data
player_info = fighter_info
