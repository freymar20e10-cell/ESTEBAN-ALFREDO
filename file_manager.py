"""
BT-7274 - Módulo de Gestión de Archivos
Crear, leer, mover, copiar, organizar archivos y carpetas.
"""

import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

from security import is_protected_path, request_confirmation, is_dangerous_command
from logger import log_action


# Extensiones organizadas por categoría
FILE_CATEGORIES = {
    "Imágenes": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
    "Música": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "Documentos": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
    "Comprimidos": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Código": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".ts", ".json", ".xml"],
    "Ejecutables": [".exe", ".msi", ".bat", ".cmd"],
    "Otros": [],
}


def list_files(path: str, show_hidden: bool = False) -> str:
    """Lista archivos y carpetas en una ruta."""
    try:
        target = Path(path).expanduser().resolve()

        if not target.exists():
            return f"❌ La ruta no existe: {target}"

        if not target.is_dir():
            return f"❌ No es una carpeta: {target}"

        if is_protected_path(str(target)):
            confirmed = request_confirmation(f"Acceder a carpeta protegida: {target}")
            if not confirmed:
                return "🚫 Acceso cancelado."

        items = list(target.iterdir())

        if not items:
            return f"📂 La carpeta está vacía: {target}"

        folders = []
        files = []

        for item in sorted(items):
            if not show_hidden and item.name.startswith("."):
                continue
            if item.is_dir():
                folders.append(f"  📁 {item.name}/")
            else:
                size = item.stat().st_size
                size_str = _format_size(size)
                files.append(f"  📄 {item.name} ({size_str})")

        result = f"📂 Contenido de: {target}\n"
        result += f"   ({len(folders)} carpetas, {len(files)} archivos)\n\n"

        if folders:
            result += "Carpetas:\n" + "\n".join(folders) + "\n\n"
        if files:
            result += "Archivos:\n" + "\n".join(files)

        log_action(f"Listó archivos en: {target}")
        return result

    except PermissionError:
        return f"❌ Sin permisos para acceder a: {path}"
    except Exception as e:
        return f"❌ Error: {e}"


def create_folder(path: str) -> str:
    """Crea una carpeta nueva."""
    try:
        target = Path(path).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        log_action(f"Creó carpeta: {target}")
        return f"✅ Carpeta creada: {target}"
    except Exception as e:
        return f"❌ Error al crear carpeta: {e}"


def create_file(path: str, content: str = "") -> str:
    """Crea un archivo nuevo con contenido opcional."""
    try:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        log_action(f"Creó archivo: {target}")
        return f"✅ Archivo creado: {target}"
    except Exception as e:
        return f"❌ Error al crear archivo: {e}"


def read_file(path: str) -> str:
    """Lee el contenido de un archivo de texto."""
    try:
        target = Path(path).expanduser().resolve()

        if not target.exists():
            return f"❌ El archivo no existe: {target}"

        if not target.is_file():
            return f"❌ No es un archivo: {target}"

        if is_protected_path(str(target)):
            confirmed = request_confirmation(f"Leer archivo en ruta protegida: {target}")
            if not confirmed:
                return "🚫 Lectura cancelada."

        # Limitar lectura a archivos de texto razonables (< 1MB)
        size = target.stat().st_size
        if size > 1_000_000:
            return f"⚠️ Archivo muy grande ({_format_size(size)}). Solo leo archivos de texto < 1MB."

        content = target.read_text(encoding="utf-8", errors="replace")
        log_action(f"Leyó archivo: {target}")

        # Truncar si es muy largo para mostrar
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (truncado, archivo muy largo)"

        return f"📄 Contenido de {target.name}:\n\n{content}"

    except Exception as e:
        return f"❌ Error al leer archivo: {e}"


def move_file(source: str, destination: str) -> str:
    """Mueve un archivo o carpeta."""
    try:
        src = Path(source).expanduser().resolve()
        dst = Path(destination).expanduser().resolve()

        if not src.exists():
            return f"❌ No existe: {src}"

        # Si el destino es una carpeta, mover dentro de ella
        if dst.is_dir():
            dst = dst / src.name

        confirmed = request_confirmation(f"Mover: {src} → {dst}")
        if not confirmed:
            return "🚫 Movimiento cancelado."

        shutil.move(str(src), str(dst))
        log_action(f"Movió: {src} → {dst}")
        return f"✅ Movido: {src.name} → {dst}"

    except Exception as e:
        return f"❌ Error al mover: {e}"


def copy_file(source: str, destination: str) -> str:
    """Copia un archivo o carpeta."""
    try:
        src = Path(source).expanduser().resolve()
        dst = Path(destination).expanduser().resolve()

        if not src.exists():
            return f"❌ No existe: {src}"

        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            # Si destino es carpeta, copiar dentro
            if dst.is_dir():
                dst = dst / src.name
            shutil.copy2(str(src), str(dst))

        log_action(f"Copió: {src} → {dst}")
        return f"✅ Copiado: {src.name} → {dst}"

    except Exception as e:
        return f"❌ Error al copiar: {e}"


def rename_file(path: str, new_name: str) -> str:
    """Renombra un archivo o carpeta."""
    try:
        target = Path(path).expanduser().resolve()

        if not target.exists():
            return f"❌ No existe: {target}"

        new_path = target.parent / new_name
        target.rename(new_path)
        log_action(f"Renombró: {target.name} → {new_name}")
        return f"✅ Renombrado: {target.name} → {new_name}"

    except Exception as e:
        return f"❌ Error al renombrar: {e}"


def delete_file(path: str) -> str:
    """Elimina un archivo o carpeta (SIEMPRE pide confirmación)."""
    try:
        target = Path(path).expanduser().resolve()

        if not target.exists():
            return f"❌ No existe: {target}"

        confirmed = request_confirmation(f"ELIMINAR: {target}")
        if not confirmed:
            return "🚫 Eliminación cancelada."

        if target.is_dir():
            shutil.rmtree(str(target))
        else:
            target.unlink()

        log_action(f"Eliminó: {target}")
        return f"✅ Eliminado: {target}"

    except Exception as e:
        return f"❌ Error al eliminar: {e}"


def search_files(directory: str, query: str) -> str:
    """Busca archivos por nombre en una carpeta (recursivo)."""
    try:
        target = Path(directory).expanduser().resolve()

        if not target.exists() or not target.is_dir():
            return f"❌ Carpeta no válida: {target}"

        results = []
        query_lower = query.lower()

        for item in target.rglob("*"):
            if query_lower in item.name.lower():
                relative = item.relative_to(target)
                icon = "📁" if item.is_dir() else "📄"
                results.append(f"  {icon} {relative}")

            # Limitar resultados
            if len(results) >= 50:
                results.append("  ... (más de 50 resultados, sé más específico)")
                break

        if not results:
            return f"🔍 No se encontró nada con '{query}' en {target}"

        log_action(f"Buscó '{query}' en {target} ({len(results)} resultados)")
        return f"🔍 Resultados para '{query}' en {target}:\n\n" + "\n".join(results)

    except Exception as e:
        return f"❌ Error en búsqueda: {e}"


def organize_folder(path: str) -> str:
    """Organiza archivos de una carpeta por tipo (extensión)."""
    try:
        target = Path(path).expanduser().resolve()

        if not target.exists() or not target.is_dir():
            return f"❌ Carpeta no válida: {target}"

        confirmed = request_confirmation(f"Organizar archivos en: {target}\n   (Moverá archivos a subcarpetas por tipo)")
        if not confirmed:
            return "🚫 Organización cancelada."

        moved_count = 0
        files = [f for f in target.iterdir() if f.is_file()]

        for file in files:
            ext = file.suffix.lower()
            category = "Otros"

            for cat_name, extensions in FILE_CATEGORIES.items():
                if ext in extensions:
                    category = cat_name
                    break

            # Crear subcarpeta de categoría
            cat_folder = target / category
            cat_folder.mkdir(exist_ok=True)

            # Mover archivo
            destination = cat_folder / file.name
            if destination.exists():
                # Agregar timestamp si ya existe
                stem = file.stem
                destination = cat_folder / f"{stem}_{int(datetime.now().timestamp())}{ext}"

            shutil.move(str(file), str(destination))
            moved_count += 1

        log_action(f"Organizó {moved_count} archivos en {target}")
        return f"✅ Organización completa: {moved_count} archivos movidos a subcarpetas por tipo."

    except Exception as e:
        return f"❌ Error al organizar: {e}"


def open_file(path: str) -> str:
    """Abre un archivo con su programa predeterminado."""
    try:
        target = Path(path).expanduser().resolve()

        if not target.exists():
            return f"❌ No existe: {target}"

        os.startfile(str(target))
        log_action(f"Abrió archivo: {target}")
        return f"✅ Abriendo: {target.name}"

    except Exception as e:
        return f"❌ Error al abrir: {e}"


def _format_size(bytes_size: int) -> str:
    """Formatea tamaño de archivo a formato legible."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"
