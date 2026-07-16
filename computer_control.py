"""
BT-7274 — Control Universal del Computador
Controla mouse, teclado y ventanas de CUALQUIER aplicación.
Combina: pyautogui (mouse/teclado) + visión de pantalla (análisis).
"""

import threading
import time
import pyautogui
import pygetwindow as gw

from logger import log_action, log_error
from security import request_confirmation

# Seguridad: pyautogui tiene un failsafe — si mueves el mouse a esquina
# superior izquierda, cancela todo. Lo dejamos activo.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3  # Pausa entre acciones para estabilidad

# Tomar el control del mouse/teclado pide confirmación una vez y queda
# "armado" por un rato corto, para no interrumpir con un aviso por cada
# clic de una misma tarea. Se aplica sin importar si la orden vino del
# chat de texto o del modo de voz en vivo — ambos pasan por aquí.
_control_lock = threading.Lock()
_control_granted_until = 0.0
CONTROL_GRANT_SECONDS = 90


def _confirm_control(description: str) -> bool:
    global _control_granted_until
    now = time.monotonic()
    with _control_lock:
        if now < _control_granted_until:
            _control_granted_until = now + CONTROL_GRANT_SECONDS
            return True
    approved = request_confirmation(description)
    if approved:
        with _control_lock:
            _control_granted_until = time.monotonic() + CONTROL_GRANT_SECONDS
    return approved


# ═══════════════════════════════════════════
# MOUSE
# ═══════════════════════════════════════════

def mouse_click(x: int, y: int) -> str:
    """Hace click en coordenadas específicas."""
    if not _confirm_control(f"Tomar control del mouse y hacer click en ({x}, {y})"):
        return "🚫 Click cancelado: no se autorizó el control del mouse."
    try:
        pyautogui.click(x, y)
        log_action(f"Click en ({x}, {y})")
        return f"👆 Click en ({x}, {y})"
    except Exception as e:
        return f"❌ Error: {e}"


def mouse_double_click(x: int, y: int) -> str:
    """Doble click en coordenadas."""
    if not _confirm_control(f"Tomar control del mouse y hacer doble click en ({x}, {y})"):
        return "🚫 Doble click cancelado: no se autorizó el control del mouse."
    try:
        pyautogui.doubleClick(x, y)
        log_action(f"Doble click en ({x}, {y})")
        return f"👆👆 Doble click en ({x}, {y})"
    except Exception as e:
        return f"❌ Error: {e}"


def mouse_right_click(x: int, y: int) -> str:
    """Click derecho."""
    if not _confirm_control(f"Tomar control del mouse y hacer click derecho en ({x}, {y})"):
        return "🚫 Click derecho cancelado: no se autorizó el control del mouse."
    try:
        pyautogui.rightClick(x, y)
        log_action(f"Click derecho en ({x}, {y})")
        return f"👆 Click derecho en ({x}, {y})"
    except Exception as e:
        return f"❌ Error: {e}"


def mouse_move(x: int, y: int) -> str:
    """Mueve el mouse a una posición."""
    try:
        pyautogui.moveTo(x, y, duration=0.3)
        return f"🖱️ Mouse movido a ({x}, {y})"
    except Exception as e:
        return f"❌ Error: {e}"


def mouse_scroll(clicks: int = -3) -> str:
    """Scroll (negativo = abajo, positivo = arriba)."""
    try:
        pyautogui.scroll(clicks)
        direction = "abajo" if clicks < 0 else "arriba"
        return f"📜 Scroll {direction}"
    except Exception as e:
        return f"❌ Error: {e}"


# ═══════════════════════════════════════════
# TECLADO
# ═══════════════════════════════════════════

def type_text(text: str) -> str:
    """Escribe texto donde esté el cursor."""
    preview = text if len(text) <= 80 else text[:80] + "…"
    if not _confirm_control(f"Tomar control del teclado y escribir: '{preview}'"):
        return "🚫 Escritura cancelada: no se autorizó el control del teclado."
    try:
        if text.isascii():
            # ASCII: typewrite directo (más rápido)
            pyautogui.typewrite(text, interval=0.02)
        else:
            # No-ASCII (español, emojis, etc): clipboard
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
        
        log_action(f"Escribió: {text[:30]}")
        return f"Escribi: '{text}'"
    except Exception as e:
        log_error("computer_control", f"type_text error: {e}")
        return f"Error escribiendo: {e}"


def press_key(key: str) -> str:
    """Presiona una tecla específica."""
    if not _confirm_control(f"Tomar control del teclado y presionar: {key}"):
        return "🚫 Tecla cancelada: no se autorizó el control del teclado."
    try:
        pyautogui.press(key)
        log_action(f"Tecla: {key}")
        return f"⌨️ Presioné: {key}"
    except Exception as e:
        return f"❌ Error: {e}"


def hotkey(*keys) -> str:
    """Presiona combinación de teclas (ej: ctrl+c, alt+f4)."""
    combo = "+".join(keys)
    if not _confirm_control(f"Tomar control del teclado y presionar la combinación: {combo}"):
        return "🚫 Combinación cancelada: no se autorizó el control del teclado."
    try:
        pyautogui.hotkey(*keys)
        log_action(f"Hotkey: {combo}")
        return f"⌨️ {combo}"
    except Exception as e:
        return f"❌ Error: {e}"


# ═══════════════════════════════════════════
# VENTANAS
# ═══════════════════════════════════════════

def focus_window(title: str) -> str:
    """Trae una ventana al frente por título (parcial)."""
    try:
        windows = gw.getWindowsWithTitle(title)
        if windows:
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.3)
            log_action(f"Ventana enfocada: {win.title}")
            return f"🪟 Ventana activada: {win.title}"
        return f"❌ No encontré ventana con título '{title}'"
    except Exception as e:
        return f"❌ Error: {e}"


def minimize_window(title: str = "") -> str:
    """Minimiza una ventana."""
    try:
        if title:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].minimize()
                return f"🪟 Minimizada: {title}"
        else:
            # Minimizar la ventana activa
            active = gw.getActiveWindow()
            if active:
                active.minimize()
                return f"🪟 Ventana minimizada"
        return "❌ No encontré la ventana"
    except Exception as e:
        return f"❌ Error: {e}"


def maximize_window(title: str = "") -> str:
    """Maximiza una ventana."""
    try:
        if title:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].maximize()
                return f"🪟 Maximizada: {title}"
        else:
            active = gw.getActiveWindow()
            if active:
                active.maximize()
                return f"🪟 Ventana maximizada"
        return "❌ No encontré la ventana"
    except Exception as e:
        return f"❌ Error: {e}"


def list_windows() -> str:
    """Lista las ventanas abiertas."""
    try:
        windows = gw.getAllWindows()
        visible = [w for w in windows if w.title.strip() and w.visible]
        result = "🪟 Ventanas abiertas:\n"
        for w in visible[:15]:
            result += f"  • {w.title}\n"
        return result
    except Exception as e:
        return f"❌ Error: {e}"


# ═══════════════════════════════════════════
# ACCIONES COMPUESTAS
# ═══════════════════════════════════════════

def copy_selection() -> str:
    """Copia la selección actual al portapapeles."""
    try:
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.2)
        import pyperclip
        content = pyperclip.paste()
        return f"📋 Copiado: {content[:100]}"
    except Exception as e:
        return f"❌ Error: {e}"


def paste_text() -> str:
    """Pega del portapapeles."""
    if not _confirm_control("Tomar control del teclado y pegar el contenido del portapapeles"):
        return "🚫 Pegado cancelado: no se autorizó el control del teclado."
    try:
        pyautogui.hotkey('ctrl', 'v')
        return "📋 Pegado"
    except Exception as e:
        return f"❌ Error: {e}"


def select_all() -> str:
    """Selecciona todo."""
    try:
        pyautogui.hotkey('ctrl', 'a')
        return "📋 Todo seleccionado"
    except Exception as e:
        return f"❌ Error: {e}"


def undo() -> str:
    """Deshacer."""
    if not _confirm_control("Tomar control del teclado y deshacer la última acción (Ctrl+Z)"):
        return "🚫 Deshacer cancelado: no se autorizó el control del teclado."
    try:
        pyautogui.hotkey('ctrl', 'z')
        return "↩️ Deshecho"
    except Exception as e:
        return f"❌ Error: {e}"


def screenshot_region(x: int, y: int, width: int, height: int) -> str:
    """Captura una región específica de la pantalla."""
    try:
        import base64, io
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        return ""
