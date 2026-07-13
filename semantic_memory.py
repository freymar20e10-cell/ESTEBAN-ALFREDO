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
    if not user_message.strip() or not assistant_message.strip():
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
    except Exception as e:
        log_action(f"No se pudo guardar memoria semántica: {e}")


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
