# -*- coding: utf-8 -*-
"""
BT-7274 - Memoria Semántica
Guarda fragmentos de conversación como embeddings y permite recuperar solo
los más relevantes para la pregunta actual, sin importar cuánto tiempo haya
pasado desde que se dijeron.

Usa ChromaDB local (sin servidor) con su función de embeddings integrada
(ligera, basada en ONNX, no depende de PyTorch ni GPU). Todo el diseño de
este módulo asume que puede fallar (sin internet la primera vez, sin
espacio en disco, etc.) y en ese caso se desactiva solo, sin romper el chat.
"""

import threading
from pathlib import Path
from datetime import datetime

from logger import log_action
from config import ASSISTANT_NAME

_CHROMA_DIR = Path(__file__).parent / "data" / "chroma_db"
_lock = threading.Lock()
_collection = None
_available = True

# Sin límites, cada turno de conversación se acumula para siempre y con los
# meses la memoria se vuelve lenta y llena de ruido ("hola", "ok", "gracias").
MIN_TURN_CHARS = 25        # intercambios más cortos que esto no aportan nada recordable
MAX_STORED_TURNS = 5000    # tope total; al superarlo se podan los más viejos
PRUNE_BATCH = 500          # cuántos se borran de una vez al podar (para no podar en cada turno)


def _get_collection():
    """Inicializa ChromaDB de forma perezosa (solo la primera vez que se usa)."""
    global _collection, _available
    if _collection is not None:
        return _collection
    if not _available:
        return None
    try:
        import chromadb
        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        _collection = client.get_or_create_collection(name="bt7274_memory")
        return _collection
    except Exception as e:
        _available = False
        log_action(f"Memoria semántica no disponible (se seguirá funcionando sin ella): {e}")
        return None


def remember_conversation_turn(user_message: str, assistant_message: str) -> None:
    """Guarda un intercambio de conversación para recordarlo semánticamente después."""
    user_message = user_message.strip()
    assistant_message = assistant_message.strip()
    if not user_message or not assistant_message:
        return
    # Saludos y confirmaciones triviales no merecen ocupar memoria a largo plazo.
    if len(user_message) + len(assistant_message) < MIN_TURN_CHARS:
        return
    collection = _get_collection()
    if collection is None:
        return
    try:
        with _lock:
            turn_id = f"turn_{datetime.now().timestamp()}"
            text = f"Usuario: {user_message}\n{ASSISTANT_NAME}: {assistant_message}"
            collection.add(
                documents=[text],
                ids=[turn_id],
                metadatas=[{"type": "conversation", "timestamp": datetime.now().isoformat()}],
            )
            _prune_if_needed(collection)
    except Exception as e:
        log_action(f"No se pudo guardar memoria semántica: {e}")


def _prune_if_needed(collection) -> None:
    """Si la memoria superó el tope, borra el lote más viejo. Los IDs son
    timestamps ('turn_<epoch>'), así que ordenarlos = ordenar por antigüedad."""
    try:
        count = collection.count()
        if count <= MAX_STORED_TURNS:
            return
        all_ids = collection.get(include=[])["ids"]
        oldest = sorted(all_ids)[:PRUNE_BATCH]
        collection.delete(ids=oldest)
        log_action(f"Memoria semántica podada: {len(oldest)} recuerdos antiguos eliminados ({count} → {count - len(oldest)})")
    except Exception as e:
        log_action(f"No se pudo podar la memoria semántica: {e}")


def recall_relevant(query: str, n_results: int = 4) -> list[str]:
    """Busca los recuerdos más relevantes semánticamente para una pregunta dada."""
    if not query.strip():
        return []
    collection = _get_collection()
    if collection is None:
        return []
    try:
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, count),
        )
        return results.get("documents", [[]])[0]
    except Exception as e:
        log_action(f"Error consultando memoria semántica: {e}")
        return []


def is_available() -> bool:
    """Para diagnóstico: indica si la memoria semántica está lista para usarse."""
    return _get_collection() is not None
