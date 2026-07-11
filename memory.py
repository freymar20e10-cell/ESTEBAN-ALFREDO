# -*- coding: utf-8 -*-
"""
BT-7274 - Módulo de Memoria Persistente (fuente única de verdad)
Guarda y recupera información entre sesiones. Thread-safe.
"""

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from logger import log_action

MEMORY_FILE = Path(__file__).parent / "data" / "bt7274_memory.json"

# Lock para evitar corrupción si dos acciones escriben casi al mismo tiempo
_memory_lock = threading.Lock()

_DEFAULT_MEMORY = {
    "preferences": {},
    "notes": [],
    "projects": {},
    "facts": [],
    "frequent_paths": [],
    "created_at": None,
    "last_session": None,
}


def _load_memory() -> dict:
    """Carga la memoria desde archivo (sin lock: usar dentro de _with_memory)."""
    if not MEMORY_FILE.exists():
        data = dict(_DEFAULT_MEMORY)
        data["created_at"] = datetime.now().isoformat()
        return data
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Autocompletar claves faltantes sin perder datos existentes
        for key, default in _DEFAULT_MEMORY.items():
            if key not in data:
                data[key] = default if not isinstance(default, (dict, list)) else type(default)()
        return data
    except (json.JSONDecodeError, OSError):
        data = dict(_DEFAULT_MEMORY)
        data["created_at"] = datetime.now().isoformat()
        return data


def _save_memory(memory: dict):
    """Guarda la memoria de forma atómica (escribe a temp y reemplaza)."""
    memory["last_session"] = datetime.now().isoformat()
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(MEMORY_FILE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, MEMORY_FILE)  # operación atómica en Windows y POSIX
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _with_memory(fn):
    """Ejecuta fn(memory) bajo lock y guarda el resultado. fn debe mutar memory in-place."""
    with _memory_lock:
        memory = _load_memory()
        result = fn(memory)
        _save_memory(memory)
        return result


# ═══════════════════════════════════════════
# HECHOS / PREFERENCIAS
# ═══════════════════════════════════════════

def remember(key: str, value: str) -> str:
    def _op(memory):
        memory["facts"].append({
            "key": key, "value": value,
            "saved_at": datetime.now().isoformat(),
        })
    _with_memory(_op)
    log_action(f"Memorizó: {key} = {value}")
    return f"🧠 Guardado en memoria: {key} → {value}"


def set_preference(key: str, value: str) -> str:
    def _op(memory):
        memory["preferences"][key] = {
            "value": value, "updated_at": datetime.now().isoformat(),
        }
    _with_memory(_op)
    log_action(f"Preferencia guardada: {key} = {value}")
    return f"✅ Preferencia guardada: {key} → {value}"


def get_preference(key: str) -> str:
    memory = _load_memory()
    pref = memory.get("preferences", {}).get(key)
    if isinstance(pref, dict):
        return pref.get("value", "")
    if isinstance(pref, str):  # compatibilidad con datos viejos
        return pref
    return ""


# ═══════════════════════════════════════════
# NOTAS
# ═══════════════════════════════════════════

def add_note(content: str) -> str:
    def _op(memory):
        memory["notes"].append({
            "content": content, "created_at": datetime.now().isoformat(),
        })
    _with_memory(_op)
    log_action(f"Nota guardada: {content[:50]}...")
    return f"📝 Nota guardada: {content}"


def get_notes() -> str:
    memory = _load_memory()
    notes = memory.get("notes", [])
    if not notes:
        return "📝 No hay notas guardadas."
    result = "📝 Tus notas:\n\n"
    for i, note in enumerate(notes, 1):
        date = note.get("created_at", "")[:10]
        result += f"  {i}. [{date}] {note['content']}\n"
    return result


def get_notes_raw(limit: int = 5) -> list:
    """Para widgets: devuelve las notas como lista (no texto formateado)."""
    memory = _load_memory()
    return memory.get("notes", [])[-limit:]


def delete_note(index: int) -> str:
    def _op(memory):
        notes = memory.get("notes", [])
        if index < 1 or index > len(notes):
            raise IndexError(f"Nota #{index} no existe. Tienes {len(notes)} notas.")
        removed = notes.pop(index - 1)
        _op.removed = removed
    try:
        _with_memory(_op)
        return f"✅ Nota #{index} eliminada: {_op.removed['content']}"
    except IndexError as e:
        return f"❌ {e}"


# ═══════════════════════════════════════════
# PROYECTOS
# ═══════════════════════════════════════════

def save_project(name: str, description: str) -> str:
    def _op(memory):
        memory["projects"][name] = {
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    _with_memory(_op)
    log_action(f"Proyecto guardado: {name}")
    return f"📋 Proyecto guardado: {name}"


def get_projects() -> str:
    memory = _load_memory()
    projects = memory.get("projects", {})
    if not projects:
        return "📋 No hay proyectos guardados."
    result = "📋 Tus proyectos:\n\n"
    for name, info in projects.items():
        result += f"  • {name}: {info['description']}\n"
    return result


# ═══════════════════════════════════════════
# CONSULTA GENERAL / CONTEXTO PARA LA IA
# ═══════════════════════════════════════════

def get_all_facts() -> str:
    memory = _load_memory()
    facts = memory.get("facts", [])
    prefs = memory.get("preferences", {})
    result = "🧠 Lo que recuerdo:\n\n"
    if prefs:
        result += "Preferencias:\n"
        for key, info in prefs.items():
            val = info["value"] if isinstance(info, dict) else info
            result += f"  • {key}: {val}\n"
        result += "\n"
    if facts:
        result += "Datos guardados:\n"
        for fact in facts[-15:]:
            result += f"  • {fact['key']}: {fact['value']}\n"
    if not prefs and not facts:
        result += "  No tengo nada guardado aún."
    return result


def get_memory_context(max_prefs: int = 12, max_facts: int = 10, max_projects: int = 8) -> str:
    """Genera un resumen de memoria para el prompt del cerebro. Con límites para
    evitar que el system prompt crezca sin control."""
    memory = _load_memory()
    context_parts = []

    prefs = memory.get("preferences", {})
    if prefs:
        items = list(prefs.items())[-max_prefs:]
        pref_lines = [f"- {k}: {v['value'] if isinstance(v, dict) else v}" for k, v in items]
        context_parts.append("PREFERENCIAS DEL USUARIO:\n" + "\n".join(pref_lines))

    facts = memory.get("facts", [])
    if facts:
        recent_facts = facts[-max_facts:]
        fact_lines = [f"- {f['key']}: {f['value']}" for f in recent_facts]
        context_parts.append("DATOS QUE RECUERDO:\n" + "\n".join(fact_lines))

    projects = memory.get("projects", {})
    if projects:
        items = list(projects.items())[-max_projects:]
        proj_lines = [f"- {name}: {info['description']}" for name, info in items]
        context_parts.append("PROYECTOS ACTIVOS:\n" + "\n".join(proj_lines))

    return "\n\n".join(context_parts) if context_parts else ""


def clear_memory() -> str:
    with _memory_lock:
        if MEMORY_FILE.exists():
            os.remove(MEMORY_FILE)
    log_action("Memoria borrada completamente")
    return "🧠 Memoria borrada por completo."
