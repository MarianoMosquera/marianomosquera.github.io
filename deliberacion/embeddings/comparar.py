
import csv
import json
import math
import os
from itertools import combinations
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).resolve().parent
RESULTADOS = BASE / "resultados"
MODELO = "text-embedding-3-large"


def distancia_coseno(a, b):
    producto = sum(x * y for x, y in zip(a, b))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(x * x for x in b))
    return 1 - producto / (norma_a * norma_b)


def calcular_pares(agentes, vectores):
    return [
        {
            "agente_1": agentes[i],
            "agente_2": agentes[j],
            "distancia": distancia_coseno(vectores[i], vectores[j])
        }
        for i, j in combinations(range(len(agentes)), 2)
    ]


def main():
    entrada = RESULTADOS / "drafts_extraidos.json"
    datos = json.loads(entrada.read_text(encoding="utf-8"))

    if len(datos) != 8:
        raise ValueError("Se esperaban exactamente ocho agentes")

    agentes = [d["agente"] for d in datos]
    if len(set(agentes)) != 8:
        raise ValueError("Hay agentes duplicados")

    textos = (
        [d["first_draft"] for d in datos]
        + [d["second_draft"] for d in datos]
    )

    if any(not texto.strip() for texto in textos):
        raise ValueError("Hay borradores vacíos")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("No se encontró OPENAI_API_KEY")

    cliente = OpenAI()
    respuesta = cliente.embeddings.create(
        model=MODELO,
        input=textos
    )

    vectores = [
        elemento.embedding
        for elemento in sorted(
            respuesta.data, key=lambda e: e.index
        )
    ]

    if len(vectores) != 16:
        raise ValueError("Se esperaban 16 embeddings")

    first = calcular_pares(agentes, vectores[:8])
    second = calcular_pares(agentes, vectores[8:])

    d1 = sum(p["distancia"] for p in first) / len(first)
    d2 = sum(p["distancia"] for p in second) / len(second)

    diferencia = d2 - d1
    porcentaje = 100 * diferencia / d1 if d1 else None

    comparaciones = [
        {
            "agente_1": a["agente_1"],
            "agente_2": a["agente_2"],
            "first_draft": a["distancia"],
            "second_draft": b["distancia"],
            "diferencia": b["distancia"] - a["distancia"]
        }
        for a, b in zip(first, second)
    ]

    resumen = {
        "metodo": "Distancia coseno media entre pares",
        "modelo": MODELO,
        "agentes": len(agentes),
        "pares": len(first),
        "diversidad_first_draft": d1,
        "diversidad_second_draft": d2,
        "diferencia_absoluta": diferencia,
        "variacion_porcentual": porcentaje
    }

    RESULTADOS.mkdir(parents=True, exist_ok=True)

    (RESULTADOS / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    with (RESULTADOS / "comparaciones.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as archivo:
        escritor = csv.DictWriter(
            archivo, fieldnames=list(comparaciones[0].keys())
        )
        escritor.writeheader()
        escritor.writerows(comparaciones)

    print("RESULTADOS DE DIVERSIDAD SEMÁNTICA")
    print(f"First Draft: {d1:.6f}")
    print(f"Second Draft: {d2:.6f}")
    print(f"Diferencia: {diferencia:+.6f}")
    print(
        f"Variación: {porcentaje:+.2f}%"
        if porcentaje is not None
        else "Variación no calculable"
    )
    print("Archivos: resumen.json y comparaciones.csv")


if __name__ == "__main__":
    main()
