"""
BT-7274 - Módulo de Seguridad
Protege contra acciones destructivas, acceso no autorizado y comandos peligrosos.
"""

from pathlib import Path

from config import DANGEROUS_KEYWORDS, PROTECTED_PATHS, DANGEROUS_EXTENSIONS

# Este callback lo inyecta server.py al arrancar. Si es None, caemos a modo
# consola SOLO cuando hay una terminal interactiva real (útil para tests/CLI).
_confirmation_backend = None


def set_confirmation_backend(fn):
    """server.py llama esto para conectar las confirmaciones a la UI (websocket)."""
    global _confirmation_backend
    _confirmation_backend = fn


def _safe_print(text: str) -> None:
    """print() que no revienta en consolas Windows con codepage viejo (cp1252)
    cuando el texto trae emojis/acentos."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def is_dangerous_command(command: str) -> bool:
    command_lower = command.lower().strip()
    safe_patterns = ["taskkill /im", "taskkill /f /im"]
    if any(command_lower.startswith(p) for p in safe_patterns):
        system_processes = ["csrss", "winlogon", "svchost", "lsass", "smss", "services"]
        if not any(proc in command_lower for proc in system_processes):
            return False
    for keyword in DANGEROUS_KEYWORDS:
        if keyword.lower() in command_lower:
            return True
    if "|" in command_lower:
        for part in command_lower.split("|"):
            part = part.strip()
            if any(kw.lower() in part for kw in DANGEROUS_KEYWORDS):
                return True
    if ">" in command_lower and any(sys_path in command_lower for sys_path in
                                     ["windows\\system32", "program files", "\\system"]):
        return True
    return False


def is_protected_path(path: str) -> bool:
    path_lower = path.lower().replace("/", "\\")
    return any(protected.lower() in path_lower for protected in PROTECTED_PATHS)


def is_dangerous_file(path: str) -> bool:
    return Path(path).suffix.lower() in DANGEROUS_EXTENSIONS


def sanitize_command(command: str) -> str:
    dangerous_chains = ["&&", "||", ";", "`", "$("]
    for chain in dangerous_chains:
        if chain in command:
            command = command.split(chain)[0].strip()
    return command


def validate_path(path: str) -> tuple[bool, str]:
    try:
        resolved = Path(path).expanduser().resolve()
        str_path = str(resolved).lower()
        if "windows\\system32" in str_path:
            return False, "No se permite acceso a System32."
        if "program files" in str_path and ("delete" in str_path or "remove" in str_path):
            return False, "No se permite eliminar archivos de Program Files."
        if is_protected_path(str(resolved)):
            return False, f"Ruta protegida: {resolved}"
        return True, ""
    except Exception as e:
        return False, f"Ruta inválida: {e}"


def validate_public_url(url: str) -> tuple[bool, str]:
    """
    Solo permite navegar a sitios web públicos normales (http/https con un
    dominio real). Bloquea esquemas peligrosos (file:, chrome:, javascript:)
    y direcciones internas del equipo o de la red local — una página
    maliciosa podría intentar que la IA navegue ahí para leer archivos
    locales o paneles internos.
    """
    from urllib.parse import urlparse
    import ipaddress

    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False, "URL inválida."

    if parsed.scheme not in ("http", "https"):
        return False, f"Solo se permite navegar a sitios web (http/https), no '{parsed.scheme}:'."

    host = (parsed.hostname or "").lower()
    if not host:
        return False, "URL sin dominio."

    if host in ("localhost", "0.0.0.0") or host.endswith(".local"):
        return False, "No se permite navegar a direcciones internas del equipo."

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False, "No se permite navegar a direcciones IP internas o reservadas."
    except ValueError:
        # No es una IP: debe parecer un dominio real (tener al menos un punto).
        if "." not in host:
            return False, f"'{host}' no parece un sitio web público."

    return True, ""


def request_confirmation(action_description: str) -> bool:
    """
    Pide confirmación. Prioridad:
    1) Si hay un backend de UI conectado (server.py lo inyecta), usarlo —
       esto muestra un diálogo real en la Web UI y espera la respuesta del
       usuario sin bloquear con input() de consola.
    2) Si no hay backend y SÍ hay terminal interactiva, usar input() (modo CLI).
    3) Si no hay ninguno de los dos, rechazar por seguridad (no colgar el hilo).
    """
    if _confirmation_backend is not None:
        try:
            return bool(_confirmation_backend(action_description))
        except Exception:
            return False

    import sys
    if not sys.stdin.isatty():
        _safe_print(f"  🚫 Acción bloqueada (sin backend de confirmación): {action_description}")
        return False

    try:
        _safe_print("\n⚠️  ACCIÓN SENSIBLE DETECTADA:")
        _safe_print(f"   {action_description}")
        response = input("   ¿Confirmas? (si/no): ").strip().lower()
        return response in ["sí", "si", "s", "yes", "y"]
    except (EOFError, OSError):
        _safe_print(f"  🚫 Acción bloqueada: {action_description}")
        return False
