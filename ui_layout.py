"""
BT-7274 — Gestión del layout de widgets
Persistencia local y acciones invocables por la IA o la UI.
"""

import json
import uuid
from copy import deepcopy
from pathlib import Path

from logger import log_action

LAYOUT_FILE = Path(__file__).parent / "data" / "ui_layout.json"

WIDGET_TYPES = {"clock", "weather", "notes", "spotify", "calendar", "tasks"}

COLOR_NAMES = {
    "verde": "#00ff88",
    "green": "#00ff88",
    "azul": "#00d4ff",
    "blue": "#00d4ff",
    "rojo": "#ff4444",
    "red": "#ff4444",
    "naranja": "#ff6b00",
    "orange": "#ff6b00",
    "morado": "#a855f7",
    "purple": "#a855f7",
    "rosa": "#ff69b4",
    "pink": "#ff69b4",
    "amarillo": "#ffd700",
    "yellow": "#ffd700",
    "blanco": "#ffffff",
    "white": "#ffffff",
}

DEFAULT_LAYOUT = {
    "theme": {
        "accent": "#00d4ff",
        "mode": "dark",
    },
    "widgets": [
        {
            "id": "w-clock",
            "type": "clock",
            "x": 0,
            "y": 0,
            "w": 2,
            "h": 1,
        },
        {
            "id": "w-weather",
            "type": "weather",
            "x": 2,
            "y": 0,
            "w": 2,
            "h": 2,
        },
        {
            "id": "w-notes",
            "type": "notes",
            "x": 0,
            "y": 1,
            "w": 2,
            "h": 2,
        },
    ],
}


def _load_layout() -> dict:
    if not LAYOUT_FILE.exists():
        return deepcopy(DEFAULT_LAYOUT)
    try:
        with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return deepcopy(DEFAULT_LAYOUT)
        data.setdefault("theme", deepcopy(DEFAULT_LAYOUT["theme"]))
        data.setdefault("widgets", [])
        return data
    except (json.JSONDecodeError, OSError):
        return deepcopy(DEFAULT_LAYOUT)


def _save_layout(layout: dict):
    LAYOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LAYOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)


def get_layout() -> dict:
    return _load_layout()


def reset_layout() -> str:
    layout = deepcopy(DEFAULT_LAYOUT)
    _save_layout(layout)
    log_action("Layout de widgets restablecido")
    return "✅ Dashboard restablecido al layout predeterminado."


def add_widget(widget_type: str, x: int = 0, y: int = 0, w: int = 2, h: int = 2) -> str:
    widget_type = (widget_type or "").lower().strip()
    if widget_type not in WIDGET_TYPES:
        types = ", ".join(sorted(WIDGET_TYPES))
        return f"❌ Widget desconocido: {widget_type}. Tipos disponibles: {types}"

    layout = _load_layout()
    widget_id = f"w-{widget_type}-{uuid.uuid4().hex[:6]}"
    layout["widgets"].append({
        "id": widget_id,
        "type": widget_type,
        "x": max(0, int(x)),
        "y": max(0, int(y)),
        "w": max(1, min(4, int(w))),
        "h": max(1, min(3, int(h))),
    })
    _save_layout(layout)
    log_action(f"Widget agregado: {widget_type} ({widget_id})")
    return f"✅ Widget de {widget_type} agregado al dashboard."


def remove_widget(widget_id: str = "", widget_type: str = "") -> str:
    layout = _load_layout()
    widgets = layout.get("widgets", [])
    if not widgets:
        return "⚠️ No hay widgets para quitar."

    target_id = (widget_id or "").strip()
    target_type = (widget_type or "").lower().strip()

    if target_id:
        filtered = [w for w in widgets if w.get("id") != target_id]
        if len(filtered) == len(widgets):
            return f"❌ No encontré el widget con id '{target_id}'."
    elif target_type:
        filtered = [w for w in widgets if w.get("type") != target_type]
        if len(filtered) == len(widgets):
            return f"❌ No hay widget de tipo '{target_type}'."
    else:
        removed = widgets.pop()
        layout["widgets"] = widgets
        _save_layout(layout)
        log_action(f"Widget eliminado: {removed.get('type')} ({removed.get('id')})")
        return f"✅ Widget de {removed.get('type')} eliminado."

    layout["widgets"] = filtered
    _save_layout(layout)
    log_action("Widget eliminado del dashboard")
    return "✅ Widget eliminado del dashboard."


def move_widget(widget_id: str = "", widget_type: str = "", x: int = 0, y: int = 0) -> str:
    layout = _load_layout()
    widgets = layout.get("widgets", [])
    target = _find_widget(widgets, widget_id, widget_type)
    if not target:
        return "❌ No encontré el widget a mover."

    target["x"] = max(0, int(x))
    target["y"] = max(0, int(y))
    _save_layout(layout)
    log_action(f"Widget movido: {target.get('type')} → ({target['x']}, {target['y']})")
    return f"✅ Widget de {target.get('type')} movido a la posición ({target['x']}, {target['y']})."


def resize_widget(widget_id: str = "", widget_type: str = "", w: int = 2, h: int = 2) -> str:
    layout = _load_layout()
    widgets = layout.get("widgets", [])
    target = _find_widget(widgets, widget_id, widget_type)
    if not target:
        return "❌ No encontré el widget a redimensionar."

    target["w"] = max(1, min(4, int(w)))
    target["h"] = max(1, min(3, int(h)))
    _save_layout(layout)
    log_action(f"Widget redimensionado: {target.get('type')} → {target['w']}x{target['h']}")
    return f"✅ Widget de {target.get('type')} redimensionado."


def set_theme(accent: str = "", mode: str = "") -> str:
    layout = _load_layout()
    theme = layout.setdefault("theme", {})

    if accent:
        color = accent.strip().lower()
        if color in COLOR_NAMES:
            color = COLOR_NAMES[color]
        elif not color.startswith("#"):
            color = f"#{color}"
        if len(color) not in (4, 7):
            return "❌ Color inválido. Usa formato hex (#00ff88) o un nombre (verde, azul, rojo...)."
        theme["accent"] = color

    if mode:
        mode = mode.lower().strip()
        if mode not in ("dark", "light"):
            return "❌ Modo inválido. Usa 'dark' o 'light'."
        theme["mode"] = mode

    _save_layout(layout)
    log_action(f"Tema actualizado: accent={theme.get('accent')}, mode={theme.get('mode')}")
    parts = []
    if accent:
        parts.append(f"color {theme.get('accent')}")
    if mode:
        parts.append(f"modo {theme.get('mode')}")
    return f"✅ Tema actualizado ({', '.join(parts)})."


def _find_widget(widgets: list, widget_id: str, widget_type: str) -> dict | None:
    if widget_id:
        for widget in widgets:
            if widget.get("id") == widget_id:
                return widget
        return None

    if widget_type:
        for widget in reversed(widgets):
            if widget.get("type") == widget_type.lower().strip():
                return widget
    return None


def get_widget_data(widget_type: str) -> dict:
    """Datos estructurados para que el frontend renderice widgets."""
    widget_type = (widget_type or "").lower().strip()

    if widget_type == "weather":
        return _weather_data()
    if widget_type == "notes":
        return _notes_data()
    if widget_type == "spotify":
        return _spotify_data()
    if widget_type == "tasks":
        return _tasks_data()
    if widget_type == "calendar":
        return _calendar_data()
    return {}


def _weather_data() -> dict:
    try:
        from internet import get_weather
        from config import DEFAULT_CITY

        raw = get_weather("")
        return {"ok": True, "text": raw, "city": DEFAULT_CITY}
    except Exception as e:
        return {"ok": False, "text": f"No se pudo obtener el clima: {e}"}


def _notes_data() -> dict:
    try:
        from memory import _load_memory
        memory = _load_memory()
        notes = memory.get("notes", [])[-5:]
        return {"ok": True, "notes": notes}
    except Exception as e:
        return {"ok": False, "notes": [], "error": str(e)}


def _spotify_data() -> dict:
    try:
        from spotify_control import spotify_now_playing
        text = spotify_now_playing()
        return {"ok": True, "text": text}
    except Exception as e:
        return {"ok": False, "text": str(e)}


def _tasks_data() -> dict:
    try:
        from scheduler import get_tasks
        raw = get_tasks(show_completed=False)
        return {"ok": True, "text": raw}
    except Exception as e:
        return {"ok": False, "text": str(e)}


def _calendar_data() -> dict:
    try:
        from scheduler import get_events_today
        raw = get_events_today()
        return {"ok": True, "text": raw}
    except Exception as e:
        return {"ok": False, "text": str(e)}
