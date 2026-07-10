"""
BT-7274 - Módulo de Seguridad
Protege contra acciones destructivas, acceso no autorizado y comandos peligrosos.
"""

import re
from pathlib import Path

from config import DANGEROUS_KEYWORDS, PROTECTED_PATHS, DANGEROUS_EXTENSIONS


def is_dangerous_command(command: str) -> bool:
    """Verifica si un comando es potencialmente peligroso."""
    command_lower = command.lower().strip()

    # Excepciones: taskkill para cerrar apps es seguro cuando BT lo ejecuta
    safe_patterns = ["taskkill /im", "taskkill /f /im"]
    if any(command_lower.startswith(p) for p in safe_patterns):
        # Solo es seguro si cierra una app normal, no procesos del sistema
        system_processes = ["csrss", "winlogon", "svchost", "lsass", "smss", "services"]
        if not any(proc in command_lower for proc in system_processes):
            return False  # Es seguro, no bloquear

    # Verificar keywords peligrosas
    for keyword in DANGEROUS_KEYWORDS:
        if keyword.lower() in command_lower:
            return True

    # Verificar pipes a comandos destructivos
    if "|" in command_lower:
        parts = command_lower.split("|")
        for part in parts:
            part = part.strip()
            if any(kw.lower() in part for kw in DANGEROUS_KEYWORDS):
                return True

    # Verificar redirección que sobrescribe archivos del sistema
    if ">" in command_lower and any(sys_path in command_lower for sys_path in
                                     ["windows\\system32", "program files", "\\system"]):
        return True

    return False


def is_protected_path(path: str) -> bool:
    """Verifica si una ruta contiene carpetas protegidas."""
    path_lower = path.lower().replace("/", "\\")
    for protected in PROTECTED_PATHS:
        if protected.lower() in path_lower:
            return True
    return False


def is_dangerous_file(path: str) -> bool:
    """Verifica si un archivo es potencialmente peligroso para ejecutar."""
    ext = Path(path).suffix.lower()
    return ext in DANGEROUS_EXTENSIONS


def sanitize_command(command: str) -> str:
    """Limpia un comando de caracteres potencialmente inyectados."""
    # Bloquear intentos de encadenar comandos ocultos
    dangerous_chains = ["&&", "||", ";", "`", "$(",  "$("]
    for chain in dangerous_chains:
        if chain in command:
            # Solo permitir el primer comando
            command = command.split(chain)[0].strip()
    return command


def validate_path(path: str) -> tuple[bool, str]:
    """
    Valida que una ruta sea segura para operar.
    Retorna (es_seguro, mensaje_error).
    """
    try:
        resolved = Path(path).expanduser().resolve()

        # No permitir acceso fuera del perfil del usuario
        user_home = Path.home()
        # Permitir acceso a drives (D:, E:, etc.) pero no a system
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


def request_confirmation(action_description: str) -> bool:
    """
    Pide confirmación al usuario antes de ejecutar algo peligroso.
    Si estamos en modo UI (no terminal interactiva), auto-rechaza para no bloquear.
    """
    import sys

    # Detectar si estamos en modo interactivo (terminal) o no
    if not sys.stdin.isatty():
        # No hay terminal interactiva — rechazar por seguridad
        print(f"  🚫 Acción bloqueada (requiere confirmación): {action_description}")
        return False

    try:
        print(f"\n⚠️  ACCIÓN SENSIBLE DETECTADA:")
        print(f"   {action_description}")
        response = input("   ¿Confirmas? (sí/no): ").strip().lower()
        return response in ["sí", "si", "s", "yes", "y"]
    except (EOFError, OSError):
        # Si no se puede leer input (modo no interactivo)
        print(f"  🚫 Acción bloqueada: {action_description}")
        return False
