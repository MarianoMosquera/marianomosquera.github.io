from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4


DECISIONES = ("Pendiente", "Aceptada", "Rechazada", "Modificar")


def fecha_actual():
    return datetime.now(timezone.utc).isoformat()


def crear_intervencion(
    categoria,
    instruccion,
    alcance,
    ubicacion="",
):
    if alcance not in ("Manuscrito completo", "Fragmento"):
        raise ValueError("Alcance no válido")

    return {
        "id": str(uuid4()),
        "categoria": categoria,
        "instruccion": instruccion,
        "alcance": alcance,
        "ubicacion": ubicacion,
        "estado": "Pendiente",
        "iteraciones": [],
        "creada_en": fecha_actual(),
    }


def agregar_propuesta(intervencion, propuesta, modelo=""):
    if intervencion["estado"] in ("Aceptada", "Rechazada"):
        raise ValueError("La intervención ya está cerrada")

    if intervencion["iteraciones"]:
        anterior = intervencion["iteraciones"][-1]
        if anterior["decision"] != "Modificar":
            raise ValueError(
                "La propuesta anterior no solicita una modificación"
            )

    resultado = deepcopy(intervencion)

    resultado["iteraciones"].append({
        "numero": len(resultado["iteraciones"]) + 1,
        "propuesta": propuesta,
        "modelo": modelo,
        "decision": "Pendiente",
        "observaciones_autor": "",
        "fecha": fecha_actual(),
    })

    resultado["estado"] = "Pendiente"
    return resultado


def decidir_propuesta(intervencion, decision, observaciones=""):
    if decision not in DECISIONES:
        raise ValueError("Decisión no válida")

    if not intervencion["iteraciones"]:
        raise ValueError("No hay propuestas para evaluar")

    resultado = deepcopy(intervencion)
    ultima = resultado["iteraciones"][-1]

    if ultima["decision"] != "Pendiente":
        raise ValueError("La propuesta ya fue evaluada")

    if decision == "Modificar" and not observaciones.strip():
        raise ValueError(
            "Para modificar, el autor debe indicar instrucciones"
        )

    ultima["decision"] = decision
    ultima["observaciones_autor"] = observaciones
    ultima["fecha_decision"] = fecha_actual()
    resultado["estado"] = decision

    return resultado


def preparar_nueva_iteracion(intervencion):
    if intervencion["estado"] != "Modificar":
        raise ValueError("No hay una modificación solicitada")

    ultima = intervencion["iteraciones"][-1]

    return {
        "intervencion_id": intervencion["id"],
        "categoria": intervencion["categoria"],
        "instruccion_original": intervencion["instruccion"],
        "alcance": intervencion["alcance"],
        "ubicacion": intervencion["ubicacion"],
        "historial": deepcopy(intervencion["iteraciones"]),
        "propuesta_anterior": ultima["propuesta"],
        "instrucciones_autor": ultima["observaciones_autor"],
    }
