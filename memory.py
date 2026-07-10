"""
BT-7274 - Módulo de Memoria Persistente
Guarda y recupera información entre sesiones.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from logger import log_action


# Archivo donde se guarda toda la memoria
MEMORY_FILE = Path(__file__).parent / "data" / "bt7274_memory.json"


def _load_memory() -> dict:
    """Carga la memoria desde archivo."""
    if not MEMORY_FILE.exists():
        return {
            "preferences": {},
            "notes": [],
            "projects": {},
            "facts": [],
            "frequent_paths": [],
            "created_at": datetime.now().isoformat(),
            "last_session": None,
        }

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {
            "preferences": {},
            "notes": [],
            "projects": {},
            "facts": [],
            "frequent_paths": [],
            "created_at": datetime.now().isoformat(),
            "last_session": None,
        }


def _save_memory(memory: dict):
    """Guarda la memoria a archivo."""
    memory["last_session"] = datetime.now().isoformat()
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def remember(key: str, value: str) -> str:
    """Guarda un dato o preferencia."""
    memory = _load_memory()

    # Guardar como hecho general
    fact = {
        "key": key,
        "value": value,
        "saved_at": datetime.now().isoformat(),
    }
    memory["facts"].append(fact)
    _save_memory(memory)
    log_action(f"Memorizó: {key} = {value}")
    return f"🧠 Guardado en memoria: {key} → {value}"


def set_preference(key: str, value: str) -> str:
    """Guarda una preferencia del usuario."""
    memory = _load_memory()
    memory["preferences"][key] = {
        "value": value,
        "updated_at": datetime.now().isoformat(),
    }
    _save_memory(memory)
    log_action(f"Preferencia guardada: {key} = {value}")
    return f"✅ Preferencia guardada: {key} → {value}"


def get_preference(key: str) -> str:
    """Obtiene una preferencia."""
    memory = _load_memory()
    pref = memory["preferences"].get(key)
    if pref:
        return pref["value"]
    return ""


def add_note(content: str) -> str:
    """Agrega una nota rápida."""
    memory = _load_memory()
    note = {
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    memory["notes"].append(note)
    _save_memory(memory)
    log_action(f"Nota guardada: {content[:50]}...")
    return f"📝 Nota guardada: {content}"


def get_notes() -> str:
    """Muestra todas las notas."""
    memory = _load_memory()
    notes = memory.get("notes", [])

    if not notes:
        return "📝 No hay notas guardadas."

    result = "📝 Tus notas:\n\n"
    for i, note in enumerate(notes, 1):
        date = note.get("created_at", "")[:10]
        result += f"  {i}. [{date}] {note['content']}\n"

    return result


def delete_note(index: int) -> str:
    """Elimina una nota por su número."""
    memory = _load_memory()
    notes = memory.get("notes", [])

    if index < 1 or index > len(notes):
        return f"❌ Nota #{index} no existe. Tienes {len(notes)} notas."

    removed = notes.pop(index - 1)
    _save_memory(memory)
    log_action(f"Nota eliminada: {removed['content'][:50]}")
    return f"✅ Nota #{index} eliminada: {removed['content']}"


def save_project(name: str, description: str) -> str:
    """Guarda información de un proyecto en curso."""
    memory = _load_memory()
    memory["projects"][name] = {
        "description": description,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _save_memory(memory)
    log_action(f"Proyecto guardado: {name}")
    return f"📋 Proyecto guardado: {name}"


def get_projects() -> str:
    """Lista todos los proyectos guardados."""
    memory = _load_memory()
    projects = memory.get("projects", {})

    if not projects:
        return "📋 No hay proyectos guardados."

    result = "📋 Tus proyectos:\n\n"
    for name, info in projects.items():
        result += f"  • {name}: {info['description']}\n"

    return result


def get_all_facts() -> str:
    """Muestra todo lo que BT recuerda."""
    memory = _load_memory()
    facts = memory.get("facts", [])
    prefs = memory.get("preferences", {})

    result = "🧠 Lo que recuerdo:\n\n"

    if prefs:
        result += "Preferencias:\n"
        for key, info in prefs.items():
            result += f"  • {key}: {info['value']}\n"
        result += "\n"

    if facts:
        result += "Datos guardados:\n"
        for fact in facts[-15:]:  # Últimos 15
            result += f"  • {fact['key']}: {fact['value']}\n"

    if not prefs and not facts:
        result += "  No tengo nada guardado aún."

    return result


def get_memory_context() -> str:
    """Genera un resumen de memoria para incluir en el prompt del cerebro."""
    memory = _load_memory()

    context_parts = []

    # Preferencias
    prefs = memory.get("preferences", {})
    if prefs:
        pref_lines = [f"- {k}: {v['value']}" for k, v in prefs.items()]
        context_parts.append("PREFERENCIAS DEL USUARIO:\n" + "\n".join(pref_lines))

    # Últimos hechos (máximo 10)
    facts = memory.get("facts", [])
    if facts:
        recent_facts = facts[-10:]
        fact_lines = [f"- {f['key']}: {f['value']}" for f in recent_facts]
        context_parts.append("DATOS QUE RECUERDO:\n" + "\n".join(fact_lines))

    # Proyectos activos
    projects = memory.get("projects", {})
    if projects:
        proj_lines = [f"- {name}: {info['description']}" for name, info in projects.items()]
        context_parts.append("PROYECTOS ACTIVOS:\n" + "\n".join(proj_lines))

    if context_parts:
        return "\n\n".join(context_parts)

    return ""


def clear_memory() -> str:
    """Borra toda la memoria (pide confirmación en el caller)."""
    if MEMORY_FILE.exists():
        os.remove(MEMORY_FILE)
    log_action("Memoria borrada completamente")
    return "🧠 Memoria borrada por completo."
