"""
BT-7274 — Sistema de caché simple.
Evita llamadas repetidas a APIs externas (clima, búsquedas, noticias).
"""

import time
import json
import os
import tempfile
import threading
from pathlib import Path

from config import DATA_DIR

CACHE_FILE = DATA_DIR / "cache.json"
_cache_lock = threading.Lock()
CACHE_TTL = {
    "weather": 600,      # 10 minutos
    "news": 1800,        # 30 minutos
    "search": 3600,      # 1 hora
    "definition": 86400, # 24 horas
}


def _load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: dict):
    tmp_path = None
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(CACHE_FILE.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        os.replace(tmp_path, CACHE_FILE)
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_cached(category: str, key: str) -> str | None:
    """Obtiene un valor del caché si no ha expirado."""
    with _cache_lock:
        cache = _load_cache()
        entry = cache.get(f"{category}:{key}")

    if not entry:
        return None

    ttl = CACHE_TTL.get(category, 600)
    if time.time() - entry.get("time", 0) > ttl:
        return None  # Expirado

    return entry.get("value")


def set_cached(category: str, key: str, value: str):
    """Guarda un valor en caché."""
    with _cache_lock:
        cache = _load_cache()
        cache[f"{category}:{key}"] = {
            "value": value,
            "time": time.time()
        }

        # Limpiar entradas viejas (máximo 200)
        if len(cache) > 200:
            sorted_keys = sorted(cache.keys(), key=lambda k: cache[k].get("time", 0))
            for old_key in sorted_keys[:50]:
                del cache[old_key]

        _save_cache(cache)
