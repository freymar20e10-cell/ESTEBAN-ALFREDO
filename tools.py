# -*- coding: utf-8 -*-
"""
BT-7274 - Catálogo único de herramientas (acciones)

Todo lo que el asistente puede hacer vive en un solo lugar: qué función lo
ejecuta, cómo se describe en el prompt de la IA, y si necesita confirmación
antes de correr. Antes esto estaba repartido en tres archivos que había que
mantener sincronizados a mano (el texto de ejemplos en brain.py, el
despachador de acciones en server.py, y la lista de confirmaciones también
en server.py) — agregar o revisar una herramienta para el chat de texto
ahora es un solo bloque aquí.

El modo de voz en vivo (voice_live.py) sigue teniendo su propia detección de
palabras clave por separado — eso es un problema distinto (adivinar qué
quiso decir alguien hablando) y no pasa por este catálogo.
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from security import request_confirmation

from actions import open_app, close_app, run_command, play_youtube, play_spotify_search, get_system_info
from file_manager import (
    list_files, create_folder, create_file, read_file,
    move_file, copy_file, rename_file, delete_file,
    search_files, organize_folder, open_file,
)
from shared_memory import (
    remember, set_preference, add_note, get_notes,
    delete_note, save_project, get_projects, get_all_facts, clear_memory,
)
from scheduler import (
    add_event, get_events_today, get_events_by_date, get_events_week,
    delete_event, add_task, get_tasks, complete_task, delete_task,
    add_reminder, get_reminders, get_daily_summary,
)
from internet import get_weather, web_search, open_url, search_and_open, get_news, get_datetime, get_definition
from spotify_control import (
    authenticate as spotify_authenticate, spotify_play, spotify_pause,
    spotify_next, spotify_previous, spotify_volume, spotify_now_playing,
    spotify_shuffle, spotify_repeat,
)
from computer_control import (
    mouse_click, mouse_double_click, mouse_right_click, mouse_move, mouse_scroll,
    type_text, press_key, hotkey,
    focus_window, minimize_window, maximize_window, list_windows,
    copy_selection, paste_text, select_all, undo,
)
from browser_control import (
    browser_search, browser_go_to, browser_click, browser_type,
    browser_type_and_enter, browser_read_page, browser_back,
    browser_new_tab, browser_close_tab, browser_scroll, close_browser,
)
from ui_layout import add_widget, remove_widget, move_widget, resize_widget, set_theme, reset_layout


@dataclass
class Tool:
    name: str
    handler: Callable[[dict], str]
    example: dict                      # params de ejemplo, para el prompt de la IA
    note: str = ""                      # línea extra de aclaración bajo el ejemplo
    confirm: Optional[str] = None       # descripción a mostrar si necesita confirmación
    synthesize: bool = False            # True = el resultado crudo se convierte en respuesta natural
    ui_action: bool = False             # True = tras ejecutar, se retransmite el layout a la UI
    group: str = "action"               # "action" o "widget" (secciones separadas en el prompt)
    extra_examples: tuple = field(default_factory=tuple)  # (etiqueta, params) adicionales


TOOLS: dict[str, Tool] = {}


def _reg(name: str, handler: Callable[[dict], str], example: dict, **kwargs) -> None:
    TOOLS[name] = Tool(name=name, handler=handler, example=example, **kwargs)


def _analyze_screen(params: dict) -> str:
    # Import local: evita que tools.py y brain.py tengan que importarse
    # entre sí al cargar (brain.py genera el prompt llamando a este catálogo).
    from brain import analyze_screen_with_ai
    return analyze_screen_with_ai(params.get("question", ""))


# ═══════════════════════════════════════════
# SISTEMA / APLICACIONES
# ═══════════════════════════════════════════
_reg("open_app", lambda p: open_app(p.get("name", "")), {"name": "spotify"})
_reg("close_app", lambda p: close_app(p.get("name", "")), {"name": "spotify"})
_reg("run_command", lambda p: run_command(p.get("command", "")), {"command": "dir"})
_reg("play_youtube", lambda p: play_youtube(p.get("query", "")), {"query": "lofi hip hop"})
_reg("play_spotify", lambda p: play_spotify_search(p.get("query", "")), {"query": "rock playlist"})
_reg("system_info", lambda p: get_system_info(), {}, synthesize=True)

# ═══════════════════════════════════════════
# ARCHIVOS
# ═══════════════════════════════════════════
_reg("list_files", lambda p: list_files(p.get("path", ".")), {"path": "C:\\Users\\FREYMAR\\Downloads"}, synthesize=True)
_reg("create_folder", lambda p: create_folder(p.get("path", "")), {"path": "C:\\Users\\FREYMAR\\Desktop\\NuevaCarpeta"})
_reg("create_file", lambda p: create_file(p.get("path", ""), p.get("content", "")),
     {"path": "C:\\Users\\FREYMAR\\Desktop\\nota.txt", "content": "contenido aquí"})
_reg("read_file", lambda p: read_file(p.get("path", "")), {"path": "C:\\Users\\FREYMAR\\Desktop\\nota.txt"}, synthesize=True)
_reg("move_file", lambda p: move_file(p.get("source", ""), p.get("destination", "")),
     {"source": "ruta_origen", "destination": "ruta_destino"})
_reg("copy_file", lambda p: copy_file(p.get("source", ""), p.get("destination", "")),
     {"source": "ruta_origen", "destination": "ruta_destino"})
_reg("rename_file", lambda p: rename_file(p.get("path", ""), p.get("new_name", "")),
     {"path": "ruta_archivo", "new_name": "nuevo_nombre.txt"})
_reg("delete_file", lambda p: delete_file(p.get("path", "")), {"path": "ruta_archivo"})
_reg("search_files", lambda p: search_files(p.get("directory", "."), p.get("query", "")),
     {"directory": "C:\\Users\\FREYMAR", "query": "nombre_buscar"}, synthesize=True)
_reg("organize_folder", lambda p: organize_folder(p.get("path", "")), {"path": "C:\\Users\\FREYMAR\\Downloads"})
_reg("open_file", lambda p: open_file(p.get("path", "")), {"path": "C:\\Users\\FREYMAR\\Desktop\\documento.pdf"})

# ═══════════════════════════════════════════
# MEMORIA / NOTAS / PROYECTOS
# ═══════════════════════════════════════════
_reg("remember", lambda p: remember(p.get("key", ""), p.get("value", "")), {"key": "color favorito", "value": "azul"})
_reg("set_preference", lambda p: set_preference(p.get("key", ""), p.get("value", "")), {"key": "idioma", "value": "español"})
_reg("add_note", lambda p: add_note(p.get("content", "")), {"content": "Comprar leche mañana"})
_reg("get_notes", lambda p: get_notes(), {}, synthesize=True)
_reg("delete_note", lambda p: delete_note(int(p.get("index", 0))), {"index": 1}, confirm="Eliminar una nota guardada")
_reg("save_project", lambda p: save_project(p.get("name", ""), p.get("description", "")),
     {"name": "BT-7274", "description": "Asistente personal IA"})
_reg("get_projects", lambda p: get_projects(), {}, synthesize=True)
_reg("get_memory", lambda p: get_all_facts(), {}, synthesize=True)
_reg("clear_memory", lambda p: clear_memory(), {}, confirm="Borrar toda la memoria del asistente")

# ═══════════════════════════════════════════
# AGENDA / TAREAS / RECORDATORIOS
# ═══════════════════════════════════════════
_reg("add_event", lambda p: add_event(p.get("title", ""), p.get("date", ""), p.get("time", ""), p.get("description", "")),
     {"title": "Reunión", "date": "2025-01-15", "time": "14:30", "description": "Con el equipo"})
_reg("get_events_today", lambda p: get_events_today(), {}, synthesize=True)
_reg("get_events_date", lambda p: get_events_by_date(p.get("date", "")), {"date": "2025-01-15"}, synthesize=True)
_reg("get_events_week", lambda p: get_events_week(), {}, synthesize=True)
_reg("delete_event", lambda p: delete_event(int(p.get("id", 0))), {"id": 1}, confirm="Eliminar un evento del calendario")
_reg("add_task", lambda p: add_task(p.get("title", ""), p.get("priority", "normal")), {"title": "Hacer ejercicio", "priority": "normal"})
_reg("get_tasks", lambda p: get_tasks(p.get("show_completed", False)), {}, synthesize=True)
_reg("complete_task", lambda p: complete_task(int(p.get("id", 0))), {"id": 1})
_reg("delete_task", lambda p: delete_task(int(p.get("id", 0))), {"id": 1}, confirm="Eliminar una tarea")
_reg("add_reminder", lambda p: add_reminder(p.get("message", ""), int(p.get("minutes", 0)), p.get("time", "")),
     {"message": "Llamar al doctor", "minutes": 30}, extra_examples=(("hora", {"message": "Reunión", "time": "14:30"}),))
_reg("get_reminders", lambda p: get_reminders(), {}, synthesize=True)
_reg("daily_summary", lambda p: get_daily_summary(), {}, synthesize=True)

# ═══════════════════════════════════════════
# INTERNET
# ═══════════════════════════════════════════
_reg("get_weather", lambda p: get_weather(p.get("city", "")), {"city": "Caracas"}, synthesize=True)
_reg("web_search", lambda p: web_search(p.get("query", "")), {"query": "qué es python"}, synthesize=True)
_reg("open_url", lambda p: open_url(p.get("url", "")), {"url": "https://google.com"})
_reg("search_google", lambda p: search_and_open(p.get("query", "")), {"query": "mejores juegos 2025"})
_reg("get_news", lambda p: get_news(p.get("category", "general")), {"category": "tecnología"}, synthesize=True)
_reg("get_datetime", lambda p: get_datetime(), {}, synthesize=True)
_reg("get_definition", lambda p: get_definition(p.get("word", "")), {"word": "resiliencia"}, synthesize=True)

# ═══════════════════════════════════════════
# SPOTIFY
# ═══════════════════════════════════════════
_reg("spotify_connect", lambda p: spotify_authenticate(), {})
_reg("spotify_play", lambda p: spotify_play(p.get("query", "")), {"query": "Bohemian Rhapsody"}, extra_examples=(("reanudar", {}),))
_reg("spotify_pause", lambda p: spotify_pause(), {})
_reg("spotify_next", lambda p: spotify_next(), {})
_reg("spotify_previous", lambda p: spotify_previous(), {})
_reg("spotify_volume", lambda p: spotify_volume(int(p.get("level", 50))), {"level": 70})
_reg("spotify_now_playing", lambda p: spotify_now_playing(), {}, synthesize=True)
_reg("spotify_shuffle", lambda p: spotify_shuffle(p.get("state", True)), {"state": True})
_reg("spotify_repeat", lambda p: spotify_repeat(p.get("state", "off")), {"state": "track"})

# ═══════════════════════════════════════════
# MOUSE / TECLADO / VENTANAS
# (la confirmación de estas vive dentro de computer_control.py, no aquí —
#  así protege por igual al chat de texto y al modo de voz en vivo)
# ═══════════════════════════════════════════
_reg("mouse_click", lambda p: mouse_click(int(p.get("x", 0)), int(p.get("y", 0))), {"x": 500, "y": 300})
_reg("mouse_double_click", lambda p: mouse_double_click(int(p.get("x", 0)), int(p.get("y", 0))), {"x": 500, "y": 300})
_reg("mouse_right_click", lambda p: mouse_right_click(int(p.get("x", 0)), int(p.get("y", 0))), {"x": 500, "y": 300})
_reg("mouse_move", lambda p: mouse_move(int(p.get("x", 0)), int(p.get("y", 0))), {"x": 500, "y": 300})
_reg("mouse_scroll", lambda p: mouse_scroll(int(p.get("clicks", -3))), {"clicks": -3})
_reg("type_text", lambda p: type_text(p.get("text", "")), {"text": "Hola mundo"})
_reg("press_key", lambda p: press_key(p.get("key", "")), {"key": "enter"})
_reg("hotkey", lambda p: hotkey(*p.get("keys", [])), {"keys": ["ctrl", "c"]})
_reg("focus_window", lambda p: focus_window(p.get("title", "")), {"title": "Chrome"})
_reg("minimize_window", lambda p: minimize_window(p.get("title", "")), {"title": "Chrome"})
_reg("maximize_window", lambda p: maximize_window(p.get("title", "")), {"title": "Chrome"})
_reg("list_windows", lambda p: list_windows(), {}, synthesize=True)
_reg("copy_selection", lambda p: copy_selection(), {})
_reg("paste_text", lambda p: paste_text(), {})
_reg("select_all", lambda p: select_all(), {})
_reg("undo", lambda p: undo(), {})

# ═══════════════════════════════════════════
# NAVEGADOR (Selenium)
# ═══════════════════════════════════════════
_reg("browser_search", lambda p: browser_search(p.get("query", "")), {"query": "clima en Bogotá"})
_reg("browser_go_to", lambda p: browser_go_to(p.get("url", "")), {"url": "https://youtube.com"})
_reg("browser_click", lambda p: browser_click(p.get("text", "")), {"text": "Iniciar sesión"})
_reg("browser_type", lambda p: browser_type(p.get("text", ""), p.get("field_hint", "")), {"text": "hola", "field_hint": "buscar"})
_reg("browser_type_and_enter", lambda p: browser_type_and_enter(p.get("text", "")), {"text": "gatos graciosos"})
_reg("browser_read_page", lambda p: browser_read_page(), {}, synthesize=True)
_reg("browser_back", lambda p: browser_back(), {})
_reg("browser_new_tab", lambda p: browser_new_tab(p.get("url", "")), {"url": "https://gmail.com"})
_reg("browser_close_tab", lambda p: browser_close_tab(), {})
_reg("browser_scroll", lambda p: browser_scroll(p.get("direction", "down")), {"direction": "down"})
_reg("close_browser", lambda p: close_browser(), {}, confirm="Cerrar el navegador controlado")

# ═══════════════════════════════════════════
# VISIÓN DE PANTALLA
# ═══════════════════════════════════════════
_reg("analyze_screen", _analyze_screen, {"question": "¿qué error muestra esta ventana?"},
     note='Si el usuario no da una pregunta específica, deja "question" vacío y describirá la pantalla en general.')

# ═══════════════════════════════════════════
# UI / WIDGETS DEL DASHBOARD
# ═══════════════════════════════════════════
_reg("add_widget", lambda p: add_widget(
        p.get("type", p.get("widget", "")), int(p.get("x", 0)), int(p.get("y", 0)),
        int(p.get("w", 2)), int(p.get("h", 2))),
     {"type": "weather", "x": 0, "y": 0, "w": 2, "h": 2},
     note="Tipos: clock, weather, notes, spotify, calendar, tasks", group="widget", ui_action=True)
_reg("remove_widget", lambda p: remove_widget(p.get("id", p.get("widget_id", "")), p.get("type", p.get("widget", ""))),
     {"type": "weather"}, group="widget", ui_action=True)
_reg("move_widget", lambda p: move_widget(
        p.get("id", p.get("widget_id", "")), p.get("type", p.get("widget", "")),
        int(p.get("x", 0)), int(p.get("y", 0))),
     {"type": "weather", "x": 2, "y": 0}, group="widget", ui_action=True)
_reg("resize_widget", lambda p: resize_widget(
        p.get("id", p.get("widget_id", "")), p.get("type", p.get("widget", "")),
        int(p.get("w", 2)), int(p.get("h", 2))),
     {"type": "notes", "w": 3, "h": 2}, group="widget", ui_action=True)
_reg("set_theme", lambda p: set_theme(p.get("accent", p.get("color", "")), p.get("mode", "")),
     {"accent": "verde", "mode": "dark"},
     note="Colores por nombre: verde, azul, rojo, naranja, morado, rosa, amarillo — o hex (#00ff88)",
     group="widget", ui_action=True)
_reg("reset_layout", lambda p: reset_layout(), {}, group="widget", ui_action=True)


# Derivado del registro — para que server.py no tenga que mantener su propia
# copia de "cuáles acciones son solo informativas".
INFO_ACTIONS = frozenset(name for name, t in TOOLS.items() if t.synthesize)


def execute(action_type: str, params: dict) -> tuple[str, bool]:
    """
    Ejecuta una herramienta registrada por nombre. Lanza KeyError si no
    existe — el llamador decide qué mensaje mostrar en ese caso.
    Devuelve (resultado, es_accion_de_ui).
    """
    tool = TOOLS[action_type]
    if tool.confirm and not request_confirmation(tool.confirm):
        return "🚫 Acción cancelada por el usuario.", False
    result = tool.handler(params)
    return result, tool.ui_action


def _example_json(name: str, params: dict) -> str:
    return json.dumps({"action": name, "params": params}, ensure_ascii=False)


def _format_tool_block(tool: Tool) -> str:
    lines = [f"- {tool.name}: {_example_json(tool.name, tool.example)}"]
    for label, extra_params in tool.extra_examples:
        lines.append(f"- {tool.name} ({label}): {_example_json(tool.name, extra_params)}")
    if tool.note:
        lines.append(f"  {tool.note}")
    return "\n".join(lines)


def build_actions_prompt() -> str:
    """
    Genera el bloque de texto que brain.py inserta en el prompt del sistema:
    la lista de acciones disponibles y, aparte, la de widgets del dashboard.
    Antes este texto se mantenía a mano en brain.py, desincronizado del
    despachador real de server.py — ahora sale directo del catálogo.
    """
    action_lines = [_format_tool_block(t) for t in TOOLS.values() if t.group == "action"]
    widget_lines = [_format_tool_block(t) for t in TOOLS.values() if t.group == "widget"]

    parts = ["\n".join(action_lines)]
    parts.append("\nINTERFAZ DE WIDGETS (puedes modificar el dashboard del usuario):")
    parts.append("\n".join(widget_lines))
    return "\n".join(parts) + "\n"
