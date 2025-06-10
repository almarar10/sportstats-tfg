# helpers/cache.py
"""
Disk-cache JSON con TTL (default 6 h).
Uso:
    from helpers.cache import cache_get, cache_set
"""
import json, time, shelve, pathlib, contextlib

PATH = pathlib.Path(".cache")
PATH.mkdir(exist_ok=True)

DB = shelve.open(str(PATH / "api_cache"), writeback=False)
TTL = 6 * 3600      # 6 horas

def _key(url: str, params: dict) -> str:
    p = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{url}?{p}"

def cache_get(url: str, params: dict):
    k = _key(url, params)
    with contextlib.suppress(KeyError):
        ts, data = DB[k]
        if time.time() - ts < TTL:
            return data          # HIT
        del DB[k]                # expired
    return None                  # MISS

def cache_set(url: str, params: dict, data):
    DB[_key(url, params)] = (time.time(), data)
