"""Registro de auditoría de TEST-IA."""

from datetime import datetime, timezone
from uuid import uuid4


def crear_registro(
    documento,
    categoria,
    instruccion_especifica,
    instruccion_general,
    propuesta="",
    ubicacion="",
):
    """Crea una intervención pendiente de decisión del autor."""
    return {
        "id": str(uuid4()),
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "documento": documento,
        "categoria": categoria,
        "instruccion_general": instruccion_general,
        "instruccion_especifica": instruccion_especifica,
        "ubicacion": ubicacion,
        "propuesta_ia": propuesta,
        "decision_autor": "Pendiente",
        "observaciones_autor": "",
    }


def registrar_decision(registro, decision, observaciones=""):
    """Registra una decisión explícita del autor."""
    decisiones_validas = {
        "Pendiente",
        "Aceptada",
        "Rechazada",
        "Modificada",
    }

    if decision not in decisiones_validas:
        raise ValueError("Decisión no válida")

    actualizado = registro.copy()
    actualizado["decision_autor"] = decision
    actualizado["observaciones_autor"] = observaciones
    return actualizado


def registro_desde_intervencion(intervencion, instruccion_general=""):
    """Representa una intervención iterativa en la auditoría."""
    historial = intervencion.get("iteraciones", [])
    ultima = historial[-1] if historial else {}

    decision = ultima.get("decision", "Pendiente")
    if decision == "Modificar":
        decision = "Modificada"

    return {
        "id": intervencion["id"],
        "fecha_utc": intervencion["creada_en"],
        "documento": intervencion.get("documento", ""),
        "categoria": intervencion["categoria"],
        "instruccion_general": instruccion_general,
        "instruccion_especifica": intervencion["instruccion"],
        "ubicacion": intervencion.get("ubicacion", ""),
        "alcance": intervencion["alcance"],
        "fragmento": intervencion.get("fragmento", ""),
        "propuesta_ia": ultima.get("propuesta", ""),
        "decision_autor": decision,
        "observaciones_autor": ultima.get("observaciones_autor", ""),
        "iteraciones": historial,
    }
