# helpers/session.py
import os, logging, requests
from requests.adapters import HTTPAdapter, Retry

log = logging.getLogger("session")

MAX_CALLS = int(os.getenv("API_MONTHLY_LIMIT", 950))   # free = 1000 / mes
_calls = 0                                             # contador global

def calls_left() -> int:
    return MAX_CALLS - _calls

def _count():
    global _calls
    if _calls >= MAX_CALLS:
        raise RuntimeError("Límite mensual API agotado")
    _calls += 1

def build():
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=.4)))
    s.headers.update({"User-Agent": "SportsApp/1.0"})
    return s

HTTP = build()
API_SPORTS_KEY = os.getenv("API_SPORTS_KEY", "")
def api_sports_headers():
    return {"x-apisports-key": API_SPORTS_KEY}
