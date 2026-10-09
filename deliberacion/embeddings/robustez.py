
import csv
import json
import math
import os
from itertools import combinations
from pathlib import Path

import tiktoken
from openai import OpenAI

BASE = Path(__file__).resolve().parent
RESULTADOS = BASE / "resultados"
MODELO = "text-embedding-3-large"


def distancia_coseno(a, b):
    producto = sum(x * y for x, y in zip(a, b))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(y * y for y in b))
    if norma_a == 0 or norma_b == 0:
        raise ValueError("Vector de norma cero")
    return 1 - producto / (norma_a * norma_b)


def diversidad(vectores):
    distancias = [
        distancia_coseno(vectores[i], vectores[j])
        for i, j in combinations(range(len(vectores)), 2)
    ]
    return sum(distancias) / len(distancias), distancias


def main():
    datos = json.loads(
        (RESULTADOS / "drafts_extraidos.json").read_text(
            encoding="utf-8"
        )
    )

    if len(datos) != 8:
        raise ValueError("Se requieren ocho agentes")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Falta OPENAI_API_KEY")

    encoder = tiktoken.get_encoding("cl100k_base")

    agentes = []
    first_textos = []
    second_textos = []
    longitudes = []

    for registro in datos:
        agente = registro["agente"]
        first = registro["first_draft"]
        second = registro["second_draft"]

        first_tokens = encoder.encode(first)
        second_tokens = encoder.encode(second)

        if not first_tokens or not second_tokens:
            raise ValueError(f"Texto vacío: {agente}")

        if len(second_tokens) < len(first_tokens):
            raise ValueError(
                f"Second Draft más corto que First Draft: {agente}"
            )

        longitud = len(first_tokens)
        second_ajustado = encoder.decode(
            second_tokens[:longitud]
        )

        agentes.append(agente)
        first_textos.append(first)
        second_textos.append(second_ajustado)

        longitudes.append({
            "agente": agente,
            "first_tokens": longitud,
            "second_original_tokens": len(second_tokens),
            "second_ajustado_tokens": len(
                encoder.encode(second_ajustado)
            )
        })

    textos = first_textos + second_textos

    if any(
        len(encoder.encode(texto)) > 8191
        for texto in textos
    ):
        raise ValueError("Se supera el límite de tokens")

    print("Generando 16 embeddings para robustez...")

    respuesta = OpenAI().embeddings.create(
        model=MODELO,
        input=textos
    )

    vectores = [
        elemento.embedding
        for elemento in sorted(
            respuesta.data,
            key=lambda elemento: elemento.index
        )
    ]

    if len(vectores) != 16:
        raise ValueError("Se esperaban 16 embeddings")

    d1, distancias_first = diversidad(vectores[:8])
    d2, distancias_second = diversidad(vectores[8:])

    diferencia = d2 - d1
    porcentaje = 100 * diferencia / d1 if d1 else None

    resumen = {
        "metodo": "Distancia coseno media entre pares",
        "control": "Second Draft truncado a la longitud del First Draft por agente",
        "modelo": MODELO,
        "agentes": len(agentes),
        "pares": len(distancias_first),
        "diversidad_first_draft": d1,
        "diversidad_second_draft_ajustado": d2,
        "diferencia_absoluta": diferencia,
        "variacion_porcentual": porcentaje,
        "longitudes": longitudes
    }

    destino = RESULTADOS / "robustez_longitud.json"
    destino.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    filas = []
    for (i, j), a, b in zip(
        combinations(range(8), 2),
        distancias_first,
        distancias_second
    ):
        filas.append({
            "agente_1": agentes[i],
            "agente_2": agentes[j],
            "first_draft": a,
            "second_draft_ajustado": b,
            "diferencia": b - a
        })

    with (RESULTADOS / "robustez_pares.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=list(filas[0].keys())
        )
        escritor.writeheader()
        escritor.writerows(filas)

    print("\nRESULTADOS DE ROBUSTEZ")
    print(f"First Draft: {d1:.6f}")
    print(f"Second Draft ajustado: {d2:.6f}")
    print(f"Diferencia: {diferencia:+.6f}")
    print(
        f"Variación: {porcentaje:+.2f}%"
        if porcentaje is not None
        else "Variación no calculable"
    )
    print("Archivos: robustez_longitud.json y robustez_pares.csv")


if __name__ == "__main__":
    main()
