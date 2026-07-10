"""
BT-7274 — Control de Navegador (Chrome)
Permite buscar, navegar, hacer click, escribir, leer páginas.
Usa Selenium con Chrome en modo que se conecta al navegador existente.
"""

import subprocess
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

from logger import log_action, log_error

# ═══════════════════════════════════════════
# ESTADO
# ═══════════════════════════════════════════

_driver = None


def _get_driver():
    """Obtiene o crea la instancia del navegador."""
    global _driver

    if _driver:
        try:
            # Verificar que sigue vivo
            _driver.title
            return _driver
        except Exception:
            _driver = None

    try:
        options = Options()
        # Conectar al Chrome existente del usuario (no abre uno nuevo)
        # Primero intentar abrir Chrome con debug port
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

        try:
            _driver = webdriver.Chrome(options=options)
            log_action("Chrome: conectado al navegador existente")
            return _driver
        except Exception:
            pass

        # Si no hay Chrome con debug, abrir uno nuevo
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        # No usar headless, queremos ver el navegador
        _driver = webdriver.Chrome(options=options)
        log_action("Chrome: nuevo navegador abierto")
        return _driver

    except Exception as e:
        log_error("browser", f"No se pudo iniciar Chrome: {e}")
        return None


def _ensure_driver() -> str | None:
    """Verifica que el driver está listo. Retorna error o None."""
    driver = _get_driver()
    if not driver:
        return "❌ No pude conectarme a Chrome. Asegúrate de que está instalado."
    return None


# ═══════════════════════════════════════════
# ACCIONES DEL NAVEGADOR
# ═══════════════════════════════════════════

def browser_search(query: str) -> str:
    """Busca algo en Google."""
    err = _ensure_driver()
    if err:
        return err

    try:
        _driver.get(f"https://www.google.com/search?q={query}")
        time.sleep(1)
        log_action(f"Chrome: buscó '{query}'")

        # Obtener primeros resultados
        results = []
        try:
            elements = _driver.find_elements(By.CSS_SELECTOR, "h3")[:5]
            for el in elements:
                results.append(el.text)
        except Exception:
            pass

        if results:
            return f"🔍 Buscando '{query}' en Google.\nPrimeros resultados:\n" + "\n".join(f"  • {r}" for r in results if r)
        return f"🔍 Buscando '{query}' en Google."

    except Exception as e:
        log_error("browser", f"Error en búsqueda: {e}")
        return f"❌ Error al buscar: {e}"


def browser_go_to(url: str) -> str:
    """Navega a una URL específica."""
    err = _ensure_driver()
    if err:
        return err

    if not url.startswith("http"):
        url = "https://" + url

    try:
        _driver.get(url)
        time.sleep(2)
        title = _driver.title
        log_action(f"Chrome: navegó a {url}")
        return f"🌐 Navegando a: {url}\nPágina: {title}"
    except Exception as e:
        log_error("browser", f"Error navegando: {e}")
        return f"❌ Error al navegar: {e}"


def browser_click(text: str) -> str:
    """Hace click en un elemento que contenga el texto indicado."""
    err = _ensure_driver()
    if err:
        return err

    try:
        # Buscar por texto visible
        wait = WebDriverWait(_driver, 5)
        element = wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
        ))
        element.click()
        time.sleep(1)
        log_action(f"Chrome: click en '{text}'")
        return f"👆 Click en '{text}'"
    except TimeoutException:
        # Intentar con links
        try:
            links = _driver.find_elements(By.PARTIAL_LINK_TEXT, text)
            if links:
                links[0].click()
                time.sleep(1)
                log_action(f"Chrome: click en link '{text}'")
                return f"👆 Click en link '{text}'"
        except Exception:
            pass
        return f"❌ No encontré un elemento con texto '{text}'"
    except Exception as e:
        return f"❌ Error al hacer click: {e}"


def browser_type(text: str, field_hint: str = "") -> str:
    """Escribe texto en un campo de la página."""
    err = _ensure_driver()
    if err:
        return err

    try:
        # Si hay hint, buscar por placeholder o label
        if field_hint:
            try:
                element = _driver.find_element(
                    By.XPATH,
                    f"//input[contains(@placeholder, '{field_hint}')] | //textarea[contains(@placeholder, '{field_hint}')]"
                )
                element.clear()
                element.send_keys(text)
                log_action(f"Chrome: escribió en '{field_hint}'")
                return f"⌨️ Escribí '{text}' en el campo '{field_hint}'"
            except NoSuchElementException:
                pass

        # Buscar el campo activo o el primer input visible
        try:
            active = _driver.switch_to.active_element
            active.clear()
            active.send_keys(text)
            log_action(f"Chrome: escribió '{text[:30]}'")
            return f"⌨️ Escribí: '{text}'"
        except Exception:
            # Buscar primer input visible
            inputs = _driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                if inp.is_displayed() and inp.get_attribute("type") in ["text", "search", ""]:
                    inp.clear()
                    inp.send_keys(text)
                    log_action(f"Chrome: escribió en input")
                    return f"⌨️ Escribí: '{text}'"

        return "❌ No encontré un campo donde escribir."
    except Exception as e:
        return f"❌ Error al escribir: {e}"


def browser_type_and_enter(text: str) -> str:
    """Escribe texto y presiona Enter (útil para búsquedas)."""
    err = _ensure_driver()
    if err:
        return err

    try:
        active = _driver.switch_to.active_element
        active.send_keys(text + Keys.RETURN)
        time.sleep(1)
        log_action(f"Chrome: escribió y enter '{text[:30]}'")
        return f"⌨️ Escribí '{text}' y presioné Enter"
    except Exception as e:
        return f"❌ Error: {e}"


def browser_read_page() -> str:
    """Lee el contenido principal de la página actual."""
    err = _ensure_driver()
    if err:
        return err

    try:
        title = _driver.title
        url = _driver.current_url

        # Obtener texto principal (evitar headers, footers, etc.)
        try:
            body = _driver.find_element(By.TAG_NAME, "main")
            text = body.text
        except Exception:
            try:
                body = _driver.find_element(By.TAG_NAME, "article")
                text = body.text
            except Exception:
                body = _driver.find_element(By.TAG_NAME, "body")
                text = body.text

        # Truncar
        if len(text) > 2000:
            text = text[:2000] + "\n... (truncado)"

        return f"📄 Página: {title}\n🔗 {url}\n\n{text}"
    except Exception as e:
        return f"❌ Error al leer: {e}"


def browser_back() -> str:
    """Retrocede una página."""
    err = _ensure_driver()
    if err:
        return err

    try:
        _driver.back()
        time.sleep(1)
        return f"⬅️ Atrás — {_driver.title}"
    except Exception as e:
        return f"❌ Error: {e}"


def browser_new_tab(url: str = "") -> str:
    """Abre una nueva pestaña."""
    err = _ensure_driver()
    if err:
        return err

    try:
        _driver.execute_script("window.open('');")
        _driver.switch_to.window(_driver.window_handles[-1])
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            _driver.get(url)
        log_action(f"Chrome: nueva pestaña {url}")
        return f"📑 Nueva pestaña abierta" + (f": {url}" if url else "")
    except Exception as e:
        return f"❌ Error: {e}"


def browser_close_tab() -> str:
    """Cierra la pestaña actual."""
    err = _ensure_driver()
    if err:
        return err

    try:
        _driver.close()
        if _driver.window_handles:
            _driver.switch_to.window(_driver.window_handles[-1])
        log_action("Chrome: pestaña cerrada")
        return "❌ Pestaña cerrada"
    except Exception as e:
        return f"❌ Error: {e}"


def browser_scroll(direction: str = "down") -> str:
    """Hace scroll en la página."""
    err = _ensure_driver()
    if err:
        return err

    try:
        if direction == "down":
            _driver.execute_script("window.scrollBy(0, 500);")
        else:
            _driver.execute_script("window.scrollBy(0, -500);")
        return f"📜 Scroll {'abajo' if direction == 'down' else 'arriba'}"
    except Exception as e:
        return f"❌ Error: {e}"


def close_browser():
    """Cierra el navegador controlado."""
    global _driver
    if _driver:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None
    return "🌐 Navegador cerrado."
