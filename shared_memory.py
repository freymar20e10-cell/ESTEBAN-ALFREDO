# -*- coding: utf-8 -*-
"""
SHARED MEMORY MODULE
Centraliza memoria y configuración compartida entre:
- server.py (PC)
- mobile/backend/app.py (móvil)
- ui/ (web)

Esto evita duplicación de código y mantiene data sincronizada.
"""

import json
from pathlib import Path
from typing import Any

# Path a data (será relativo según quien lo importe)
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

MEMORY_FILE = DATA_DIR / "bt7274_memory.json"
NOTES_FILE = DATA_DIR / "notes.json"
TASKS_FILE = DATA_DIR / "tasks.json"


# ═══════════════════════════════════════════
# MEMORY (Hechos, preferencias, historial)
# ═══════════════════════════════════════════

def _load_memory() -> dict:
    """Carga memoria desde JSON."""
    if not MEMORY_FILE.exists():
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}


def _save_memory(memory: dict):
    """Guarda memoria a JSON."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def remember(key: str, value: str) -> str:
    """Recuerda un hecho."""
    memory = _load_memory()
    memory[key] = value
    _save_memory(memory)
    return f"Recordé: {key} = {value}"


def get_memory_context() -> str:
    """Devuelve contexto de memoria para incluir en prompts de IA."""
    memory = _load_memory()
    if not memory:
        return ""
    lines = [f"{k}: {v}" for k, v in memory.items()]
    return "\n".join(lines)


# ═══════════════════════════════════════════
# PREFERENCES
# ═══════════════════════════════════════════

def set_preference(key: str, value: Any) -> str:
    """Guarda una preferencia de usuario."""
    memory = _load_memory()
    if "preferences" not in memory:
        memory["preferences"] = {}
    memory["preferences"][key] = value
    _save_memory(memory)
    return f"Preferencia guardada: {key} = {value}"


def get_preference(key: str, default=None) -> Any:
    """Obtiene una preferencia."""
    memory = _load_memory()
    return memory.get("preferences", {}).get(key, default)


# ═══════════════════════════════════════════
# NOTES
# ═══════════════════════════════════════════

def _load_notes() -> list:
    """Carga notas desde JSON."""
    if not NOTES_FILE.exists():
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def _save_notes(notes: list):
    """Guarda notas a JSON."""
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def add_note(content: str) -> str:
    """Agrega una nota."""
    notes = _load_notes()
    notes.append({"content": content, "index": len(notes)})
    _save_notes(notes)
    return f"Nota guardada: {content[:50]}"


def get_notes() -> list:
    """Obtiene todas las notas."""
    return _load_notes()


def delete_note(index: int) -> str:
    """Elimina una nota por índice."""
    notes = _load_notes()
    if 0 <= index < len(notes):
        notes.pop(index)
        _save_notes(notes)
        return "Nota eliminada."
    return "Nota no encontrada."


# ═══════════════════════════════════════════
# FILTER REASONING (para ocultar pensamiento de IA)
# ═══════════════════════════════════════════

def filter_reasoning(response: str) -> str:
    """
    Filtra secciones de 'razonamiento' que la IA genera internamente.
    Muchos modelos generan '<thinking>' o similar que no debe mostrarse.
    """
    import re
    
    # Remover <thinking>...</thinking>
    response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL | re.IGNORECASE)
    
    # Remover 'Let me think...' y frases similares
    for phrase in ["Let me think", "Okay, let me", "First, I should", "Let me break this down"]:
        response = re.sub(rf"^{re.escape(phrase)}.*?\n", "", response, flags=re.IGNORECASE | re.MULTILINE)
    
    return response.strip()


# ═══════════════════════════════════════════
# TAGS PROCESSING (Para móvil: [MEMORY:], [SPOTIFY:], etc)
# ═══════════════════════════════════════════

def process_tags(response: str) -> dict:
    """
    Interpreta tags especiales en respuestas de la IA para ejecutar acciones.
    Usado por mobile backend para ejecutar acciones.
    
    Ejemplo:
    "[MEMORY:ciudad=Bogotá] [SPOTIFY:Rara Vez]"
    → {"memory": {"ciudad": "Bogotá"}, "spotify": "Rara Vez", "text": "..."}
    """
    import re
    
    result = {"memory": {}, "actions": [], "text": response}
    
    # [MEMORY:key=value]
    for match in re.finditer(r'\[MEMORY:(\w+)=([^\]]+)\]', response):
        key, value = match.groups()
        result["memory"][key] = value
        remember(key, value)
    
    # [SPOTIFY:cancion]
    for match in re.finditer(r'\[SPOTIFY:([^\]]+)\]', response):
        song = match.group(1)
        result["actions"].append({"type": "spotify", "data": song})
    
    # [YOUTUBE:video]
    for match in re.finditer(r'\[YOUTUBE:([^\]]+)\]', response):
        video = match.group(1)
        result["actions"].append({"type": "youtube", "data": video})
    
    # [OPEN_APP:nombre]
    for match in re.finditer(r'\[OPEN_APP:([^\]]+)\]', response):
        app = match.group(1)
        result["actions"].append({"type": "open_app", "data": app})
    
    # [WHATSAPP:numero=mensaje]
    for match in re.finditer(r'\[WHATSAPP:([^\]]+)=([^\]]+)\]', response):
        target, msg = match.groups()
        result["actions"].append({"type": "whatsapp", "target": target, "message": msg})
    
    # Remover tags del texto final
    result["text"] = re.sub(r'\[(?:MEMORY|SPOTIFY|YOUTUBE|OPEN_APP|WHATSAPP):[^\]]*\]', '', response).strip()
    
    return result


# ═══════════════════════════════════════════
# PROJECTS
# ═══════════════════════════════════════════

def save_project(name: str, description: str) -> str:
    """Guarda información de un proyecto en curso."""
    memory = _load_memory()
    if "projects" not in memory:
        memory["projects"] = {}
    
    from datetime import datetime
    memory["projects"][name] = {
        "description": description,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _save_memory(memory)
    return f"Proyecto guardado: {name}"


def get_projects() -> str:
    """Lista todos los proyectos guardados."""
    memory = _load_memory()
    projects = memory.get("projects", {})

    if not projects:
        return "No hay proyectos guardados."

    result = "Tus proyectos:\n\n"
    for name, info in projects.items():
        result += f"  • {name}: {info['description']}\n"

    return result


# ═══════════════════════════════════════════
# FACTS (Hechos memorizados)
# ═══════════════════════════════════════════

def get_all_facts() -> str:
    """Muestra todo lo que se recuerda."""
    memory = _load_memory()
    facts = memory.get("facts", []) if isinstance(memory.get("facts"), list) else []
    prefs = memory.get("preferences", {})

    result = "Lo que recuerdo:\n\n"

    if prefs:
        result += "Preferencias:\n"
        for key, value in prefs.items():
            # Manejar tanto formato antiguo como nuevo
            if isinstance(value, dict):
                result += f"  • {key}: {value.get('value', value)}\n"
            else:
                result += f"  • {key}: {value}\n"
        result += "\n"

    if facts:
        result += "Datos guardados:\n"
        for fact in facts[-15:]:  # Últimos 15
            if isinstance(fact, dict) and "key" in fact:
                result += f"  • {fact['key']}: {fact['value']}\n"

    if not prefs and not facts:
        result += "  No tengo nada guardado aún."

    return result


# ═══════════════════════════════════════════
# CLEAR MEMORY
# ═══════════════════════════════════════════

def clear_memory() -> str:
    """Borra toda la memoria."""
    import os
    if MEMORY_FILE.exists():
        os.remove(MEMORY_FILE)
    return "Memoria borrada por completo."
