"""Gestión de versiones Word de TEST-IA."""

from datetime import datetime, timezone
from io import BytesIO

from docx import Document


def crear_version_original(nombre, contenido):
    """Conserva los bytes originales del documento."""
    if not nombre.lower().endswith(".docx"):
        raise ValueError("Se requiere un documento DOCX")

    Document(BytesIO(contenido))

    return {
        "numero": 0,
        "nombre": nombre,
        "contenido": bytes(contenido),
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "tipo": "Original",
    }


def crear_version_prueba(original, numero):
    """Genera una copia de prueba sin alterar el original."""
    if numero < 1:
        raise ValueError("Número de versión no válido")

    documento = Document(BytesIO(original["contenido"]))
    salida = BytesIO()
    documento.save(salida)

    return {
        "numero": numero,
        "nombre": f"version_{numero}.docx",
        "contenido": salida.getvalue(),
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "tipo": "Prueba sin modificaciones de IA",
    }
