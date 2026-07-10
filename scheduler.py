"""
BT-7274 - Módulo de Calendario, Recordatorios y Tareas
Gestiona eventos, recordatorios con alarma y lista de tareas.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from logger import log_action
from config import DATA_DIR


# Archivos de datos
EVENTS_FILE = DATA_DIR / "events.json"
TASKS_FILE = DATA_DIR / "tasks.json"
REMINDERS_FILE = DATA_DIR / "reminders.json"


def _ensure_data_dir():
    """Crea la carpeta de datos si no existe."""
    DATA_DIR.mkdir(exist_ok=True)


def _load_json(filepath: Path) -> list:
    """Carga datos desde un archivo JSON."""
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def _save_json(filepath: Path, data: list):
    """Guarda datos a un archivo JSON."""
    _ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════
# EVENTOS / CALENDARIO
# ═══════════════════════════════════════════

def add_event(title: str, date: str, time_str: str = "", description: str = "") -> str:
    """
    Agrega un evento al calendario.
    date: formato YYYY-MM-DD
    time_str: formato HH:MM (opcional)
    """
    events = _load_json(EVENTS_FILE)

    # Validar fecha
    try:
        event_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return f"❌ Formato de fecha inválido. Usa YYYY-MM-DD (ej: 2025-01-15)"

    # Validar hora si se proporciona
    if time_str:
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return f"❌ Formato de hora inválido. Usa HH:MM (ej: 14:30)"

    event = {
        "id": len(events) + 1,
        "title": title,
        "date": date,
        "time": time_str,
        "description": description,
        "created_at": datetime.now().isoformat(),
    }

    events.append(event)
    _save_json(EVENTS_FILE, events)
    log_action(f"Evento creado: {title} ({date} {time_str})")

    time_display = f" a las {time_str}" if time_str else ""
    return f"📅 Evento creado: {title} — {date}{time_display}"


def get_events_today() -> str:
    """Muestra los eventos de hoy."""
    today = datetime.now().strftime("%Y-%m-%d")
    return get_events_by_date(today)


def get_events_by_date(date: str) -> str:
    """Muestra eventos de una fecha específica."""
    events = _load_json(EVENTS_FILE)
    day_events = [e for e in events if e["date"] == date]

    if not day_events:
        return f"📅 No hay eventos para {date}."

    result = f"📅 Eventos para {date}:\n\n"
    for e in sorted(day_events, key=lambda x: x.get("time", "")):
        time_display = f" [{e['time']}]" if e.get("time") else ""
        desc = f" — {e['description']}" if e.get("description") else ""
        result += f"  • {e['title']}{time_display}{desc}\n"

    return result


def get_events_week() -> str:
    """Muestra eventos de los próximos 7 días."""
    events = _load_json(EVENTS_FILE)
    today = datetime.now()
    week_end = today + timedelta(days=7)

    today_str = today.strftime("%Y-%m-%d")
    week_end_str = week_end.strftime("%Y-%m-%d")

    week_events = [e for e in events if today_str <= e["date"] <= week_end_str]

    if not week_events:
        return "📅 No hay eventos en los próximos 7 días."

    result = "📅 Eventos de esta semana:\n\n"
    current_date = ""
    for e in sorted(week_events, key=lambda x: (x["date"], x.get("time", ""))):
        if e["date"] != current_date:
            current_date = e["date"]
            # Nombre del día
            day_name = datetime.strptime(current_date, "%Y-%m-%d").strftime("%A %d/%m")
            result += f"\n  📆 {day_name}:\n"
        time_display = f" [{e['time']}]" if e.get("time") else ""
        result += f"    • {e['title']}{time_display}\n"

    return result


def delete_event(event_id: int) -> str:
    """Elimina un evento por su ID."""
    events = _load_json(EVENTS_FILE)

    for i, event in enumerate(events):
        if event["id"] == event_id:
            removed = events.pop(i)
            _save_json(EVENTS_FILE, events)
            log_action(f"Evento eliminado: {removed['title']}")
            return f"✅ Evento eliminado: {removed['title']}"

    return f"❌ No se encontró evento con ID {event_id}."


# ═══════════════════════════════════════════
# TAREAS (TO-DO)
# ═══════════════════════════════════════════

def add_task(title: str, priority: str = "normal") -> str:
    """Agrega una tarea. Priority: alta, normal, baja."""
    tasks = _load_json(TASKS_FILE)

    task = {
        "id": len(tasks) + 1,
        "title": title,
        "priority": priority,
        "completed": False,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    tasks.append(task)
    _save_json(TASKS_FILE, tasks)
    log_action(f"Tarea creada: {title} (prioridad: {priority})")

    priority_icons = {"alta": "🔴", "normal": "🟡", "baja": "🟢"}
    icon = priority_icons.get(priority, "🟡")
    return f"✅ Tarea creada: {icon} {title}"


def get_tasks(show_completed: bool = False) -> str:
    """Lista las tareas pendientes."""
    tasks = _load_json(TASKS_FILE)

    if not show_completed:
        tasks = [t for t in tasks if not t["completed"]]
    
    if not tasks:
        return "✅ No tienes tareas pendientes. ¡Bien hecho!"

    priority_icons = {"alta": "🔴", "normal": "🟡", "baja": "🟢"}
    priority_order = {"alta": 0, "normal": 1, "baja": 2}

    tasks_sorted = sorted(tasks, key=lambda x: priority_order.get(x.get("priority", "normal"), 1))

    result = "📋 Tus tareas:\n\n"
    for t in tasks_sorted:
        icon = priority_icons.get(t.get("priority", "normal"), "🟡")
        status = "✅" if t["completed"] else "⬜"
        result += f"  {status} {icon} [{t['id']}] {t['title']}\n"

    pending = len([t for t in tasks_sorted if not t["completed"]])
    result += f"\n  Total pendientes: {pending}"
    return result


def complete_task(task_id: int) -> str:
    """Marca una tarea como completada."""
    tasks = _load_json(TASKS_FILE)

    for task in tasks:
        if task["id"] == task_id:
            if task["completed"]:
                return f"ℹ️ La tarea '{task['title']}' ya estaba completada."
            task["completed"] = True
            task["completed_at"] = datetime.now().isoformat()
            _save_json(TASKS_FILE, tasks)
            log_action(f"Tarea completada: {task['title']}")
            return f"✅ Tarea completada: {task['title']} 🎉"

    return f"❌ No se encontró tarea con ID {task_id}."


def delete_task(task_id: int) -> str:
    """Elimina una tarea."""
    tasks = _load_json(TASKS_FILE)

    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            removed = tasks.pop(i)
            _save_json(TASKS_FILE, tasks)
            log_action(f"Tarea eliminada: {removed['title']}")
            return f"✅ Tarea eliminada: {removed['title']}"

    return f"❌ No se encontró tarea con ID {task_id}."


# ═══════════════════════════════════════════
# RECORDATORIOS
# ═══════════════════════════════════════════

# Lista global de timers activos
_active_reminders = []


def add_reminder(message: str, minutes: int = 0, time_str: str = "") -> str:
    """
    Agrega un recordatorio.
    - minutes: en cuántos minutos recordar (ej: 30)
    - time_str: hora exacta HH:MM (ej: "14:30")
    Uno de los dos debe proporcionarse.
    """
    reminders = _load_json(REMINDERS_FILE)

    now = datetime.now()

    if minutes > 0:
        trigger_time = now + timedelta(minutes=minutes)
        time_display = f"en {minutes} minutos"
    elif time_str:
        try:
            target = datetime.strptime(time_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            # Si la hora ya pasó hoy, programar para mañana
            if target <= now:
                target += timedelta(days=1)
            trigger_time = target
            time_display = f"a las {time_str}"
            minutes = int((trigger_time - now).total_seconds() / 60)
        except ValueError:
            return "❌ Formato de hora inválido. Usa HH:MM (ej: 14:30)"
    else:
        return "❌ Necesito saber cuándo recordarte. Dime los minutos o la hora."

    reminder = {
        "id": len(reminders) + 1,
        "message": message,
        "trigger_time": trigger_time.isoformat(),
        "created_at": now.isoformat(),
        "triggered": False,
    }

    reminders.append(reminder)
    _save_json(REMINDERS_FILE, reminders)

    # Programar el recordatorio en segundo plano
    _schedule_reminder(message, minutes)

    log_action(f"Recordatorio creado: '{message}' {time_display}")
    return f"⏰ Recordatorio programado: '{message}' — {time_display} ({trigger_time.strftime('%H:%M')})"


def _schedule_reminder(message: str, minutes: int):
    """Programa un recordatorio en segundo plano."""
    def _alert():
        time.sleep(minutes * 60)
        print(f"\n\n🔔 ═══════════════════════════════════════")
        print(f"   RECORDATORIO: {message}")
        print(f"   ═══════════════════════════════════════ 🔔\n")
        # Intentar hacer beep del sistema
        try:
            import winsound
            winsound.Beep(1000, 500)
            winsound.Beep(1000, 500)
        except Exception:
            print("\a")  # Beep básico

    timer = threading.Thread(target=_alert, daemon=True)
    timer.start()
    _active_reminders.append(timer)


def get_reminders() -> str:
    """Muestra recordatorios pendientes."""
    reminders = _load_json(REMINDERS_FILE)
    now = datetime.now()

    pending = [r for r in reminders if not r.get("triggered", False) 
               and datetime.fromisoformat(r["trigger_time"]) > now]

    if not pending:
        return "⏰ No hay recordatorios pendientes."

    result = "⏰ Recordatorios pendientes:\n\n"
    for r in pending:
        trigger = datetime.fromisoformat(r["trigger_time"])
        result += f"  • [{r['id']}] {r['message']} — {trigger.strftime('%H:%M %d/%m')}\n"

    return result


def get_daily_summary() -> str:
    """Genera un resumen del día: eventos + tareas pendientes + recordatorios."""
    today = datetime.now().strftime("%Y-%m-%d")
    day_name = datetime.now().strftime("%A %d de %B, %Y")

    result = f"📊 Resumen del día — {day_name}\n"
    result += "═" * 45 + "\n\n"

    # Eventos de hoy
    events = _load_json(EVENTS_FILE)
    today_events = [e for e in events if e["date"] == today]
    if today_events:
        result += "📅 Eventos de hoy:\n"
        for e in sorted(today_events, key=lambda x: x.get("time", "")):
            time_display = f" [{e['time']}]" if e.get("time") else ""
            result += f"  • {e['title']}{time_display}\n"
        result += "\n"
    else:
        result += "📅 Sin eventos hoy.\n\n"

    # Tareas pendientes
    tasks = _load_json(TASKS_FILE)
    pending_tasks = [t for t in tasks if not t["completed"]]
    if pending_tasks:
        result += f"📋 Tareas pendientes ({len(pending_tasks)}):\n"
        for t in pending_tasks[:5]:  # Máximo 5
            priority_icons = {"alta": "🔴", "normal": "🟡", "baja": "🟢"}
            icon = priority_icons.get(t.get("priority", "normal"), "🟡")
            result += f"  • {icon} {t['title']}\n"
        if len(pending_tasks) > 5:
            result += f"  ... y {len(pending_tasks) - 5} más\n"
        result += "\n"
    else:
        result += "📋 ¡Sin tareas pendientes!\n\n"

    # Recordatorios
    reminders = _load_json(REMINDERS_FILE)
    now = datetime.now()
    pending_reminders = [r for r in reminders if not r.get("triggered", False)
                        and datetime.fromisoformat(r["trigger_time"]) > now]
    if pending_reminders:
        result += f"⏰ Recordatorios activos ({len(pending_reminders)}):\n"
        for r in pending_reminders:
            trigger = datetime.fromisoformat(r["trigger_time"])
            result += f"  • {r['message']} — {trigger.strftime('%H:%M')}\n"

    return result
