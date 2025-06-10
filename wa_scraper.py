# wa_scraper.py
"""
Scraper para datos de WorldAthletics.
Obtiene perfil y mejores marcas (PBs) de un atleta dado su athlete_id.
"""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import certifi
import requests
import urllib3
from bs4 import BeautifulSoup

# ── Configuración ────────────────────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://worldathletics.org"
CACHE_FILE = Path(__file__).with_name("wa_cache.json")

if CACHE_FILE.exists():
    _CACHE: Dict[str, str] = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
else:
    _CACHE = {}

NUXT_RE     = re.compile(r'window\.__NUXT__\s*=\s*(\{.*?\});', re.S)
NEXTJS_RE   = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
UA_HEADER   = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _save_cache() -> None:
    CACHE_FILE.write_text(json.dumps(_CACHE, indent=2, ensure_ascii=False), encoding="utf-8")


def _strip(text: str) -> str:
    """Normaliza texto para clave de cache."""
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn").lower()


def _fetch_html(aid: str) -> str:
    """
    Obtiene el HTML del perfil del atleta.
    Primero intenta /athletes/_/{aid}, luego /athletes/{aid}.
    """
    tried = set()
    paths = [f"/athletes/_/{aid}", f"/athletes/{aid}"]

    for path in paths:
        url = path if path.startswith("http") else BASE_URL + path
        if "worldathletics.org" in url:
            verify_val = False
        else:
            verify_val = certifi.where()
        r = requests.get(
            url,
            headers=UA_HEADER,
            timeout=15,
            verify=verify_val,
            allow_redirects=False
        )
        if r.status_code in (301, 302):
            loc = r.headers.get("Location")
            if loc and loc not in tried:
                tried.add(loc)
                paths.append(loc)
            continue
        r.raise_for_status()
        text = r.text
        if "__NUXT__" in text or "<script id=\"__NEXT_DATA__\"" in text:
            return text

    raise RuntimeError("No se pudo recuperar HTML válido con NUXT/Next block")


def _extract_json_block(html_txt: str) -> Dict[str, Any]:
    """Extrae y parsea el JSON embebido de Nuxt o Next.js."""
    m = NUXT_RE.search(html_txt)
    if m:
        return json.loads(m.group(1))

    m2 = NEXTJS_RE.search(html_txt)
    if m2:
        payload = m2.group(1)
        return json.loads(payload)

    raise RuntimeError("No se encontró bloque JSON de Nuxt/Next")


def _parse_competitor(nuxt: Dict[str, Any], aid: str) -> Dict[str, Any]:
    """
    Extrae:
      basic: { id, name, country }
      pbs: lista de { discipline, performance, season, indoor }
    """
    comp = nuxt["props"]["pageProps"]["competitor"]
    basic_data = comp["basicData"]
    basic = {
        "id":      aid,
        "name":    f"{basic_data.get('firstName')} {basic_data.get('lastName')}",
        "country": basic_data.get("countryFullName", "—")
    }

    pbs_list: List[Dict[str, Any]] = []
    for item in comp.get("personalBests", {}).get("results", []):
        pbs_list.append({
            "discipline":  item.get("discipline", ""),
            "performance": item.get("mark", ""),
            "season":      item.get("date", "")[-4:],
            "indoor":      item.get("venue", "").endswith("(i)")
        })

    return {"basic": basic, "pbs": pbs_list}


@lru_cache(maxsize=256)
def player_info(name: str, athlete_id: str = None) -> Dict[str, Any]:
    """
    Devuelve diccionario con:
      basic: perfil del atleta
      pbs: personal bests
    athlete_id es obligatorio la primera vez para cachear la ruta correcta.
    """
    key = _strip(name)

    if key in _CACHE:
        aid = _CACHE[key]
        if athlete_id and athlete_id != aid:
            _CACHE[key] = athlete_id
            _save_cache()
            aid = athlete_id
    else:
        if not athlete_id:
            raise LookupError("Se necesita athlete_id la primera vez")
        aid = athlete_id
        _CACHE[key] = aid
        _save_cache()

    html_txt = _fetch_html(aid)
    nuxt = _extract_json_block(html_txt)
    return _parse_competitor(nuxt, aid)
