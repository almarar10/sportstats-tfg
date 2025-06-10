# formula1_api.py
"""
Wrapper para consulta de pilotos de Fórmula 1 vía API-Sports v1.
Provee driver_info(name_or_id) → dict JSON de /drivers.
"""
import os
import sys
import json
from typing import Union, Dict, Any
import requests
from dotenv import load_dotenv

# ── Configuración ─────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("APISPORTS_KEY", "")
if not API_KEY:
    raise RuntimeError("Falta APISPORTS_KEY en .env para Formula 1")

BASE_URL = "https://v1.formula-1.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
    "accept": "application/json",
}


def driver_info(name_or_id: Union[str, int]) -> Dict[str, Any]:
    """
    Devuelve el JSON de /drivers.
    • Si name_or_id es int → busca por id.
    • Si es str           → busca con ?search=name.
    """
    params: Dict[str, Any]
    if isinstance(name_or_id, int):
        params = {"id": name_or_id}
    else:
        params = {"search": name_or_id}

    url = f"{BASE_URL}/drivers"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()
