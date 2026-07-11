# -*- coding: utf-8 -*-
"""
SHARED MEMORY — Compatibilidad
Este módulo YA NO tiene su propio almacenamiento. Delega todo a memory.py,
que es la fuente única de verdad, para que server.py, brain.py, internet.py
y ui_layout.py siempre vean los mismos datos.
"""

import re
from typing import Any

from memory import (
    remember as _remember,
    set_preference as _set_preference,
    get_preference as _get_preference,
    add_note as _add_note,
    get_notes_raw as _get_notes_raw,
    delete_note as _delete_note,
    save_project as _save_project,
    get_projects as _get_projects,
    get_all_facts as _get_all_facts,
    get_memory_context as _get_memory_context,
    clear_memory as _clear_memory,
)

# Re-exportados con la misma firma que antes para no romper server.py
remember = _remember
set_preference = _set_preference
get_preference = _get_preference
save_project = _save_project
get_projects = _get_projects
get_all_facts = _get_all_facts
get_memory_context = _get_memory_context
clear_memory = _clear_memory


def add_note(content: str) -> str:
    return _add_note(content)


def get_notes() -> list:
    """Server.py espera poder iterar esto para widgets; devolvemos la lista cruda."""
    return _get_notes_raw(limit=50)


def delete_note(index: int) -> str:
    """Firma 1-indexada, igual que memory.py y el prompt de brain.py."""
    return _delete_note(index)


# ═══════════════════════════════════════════
# FILTER REASONING (sin cambios respecto al original)
# ═══════════════════════════════════════════

def filter_reasoning(response: str) -> str:
    response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL | re.IGNORECASE)
    for phrase in ["Let me think", "Okay, let me", "First, I should", "Let me break this down"]:
        response = re.sub(rf"^{re.escape(phrase)}.*?\n", "", response, flags=re.IGNORECASE | re.MULTILINE)
    return response.strip()


# ═══════════════════════════════════════════
# TAGS PROCESSING (sin cambios, usado por mobile)
# ═══════════════════════════════════════════

def process_tags(response: str) -> dict:
    result = {"memory": {}, "actions": [], "text": response}
    for match in re.finditer(r'\[MEMORY:(\w+)=([^\]]+)\]', response):
        key, value = match.groups()
        result["memory"][key] = value
        remember(key, value)
    for match in re.finditer(r'\[SPOTIFY:([^\]]+)\]', response):
        result["actions"].append({"type": "spotify", "data": match.group(1)})
    for match in re.finditer(r'\[YOUTUBE:([^\]]+)\]', response):
        result["actions"].append({"type": "youtube", "data": match.group(1)})
    for match in re.finditer(r'\[OPEN_APP:([^\]]+)\]', response):
        result["actions"].append({"type": "open_app", "data": match.group(1)})
    for match in re.finditer(r'\[WHATSAPP:([^\]]+)=([^\]]+)\]', response):
        target, msg = match.groups()
        result["actions"].append({"type": "whatsapp", "target": target, "message": msg})
    result["text"] = re.sub(r'\[(?:MEMORY|SPOTIFY|YOUTUBE|OPEN_APP|WHATSAPP):[^\]]*\]', '', response).strip()
    return result
