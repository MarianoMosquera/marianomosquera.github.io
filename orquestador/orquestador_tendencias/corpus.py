"""Lectura y deduplicación del corpus OA3."""

import csv
import re
import unicodedata
from pathlib import Path

try:
    from .config import CORPUS_PATH
except ImportError:
    from config import CORPUS_PATH


ROOT = Path(__file__).resolve().parents[2]


def normalizar(texto):
    texto = unicodedata.normalize("NFKC", texto)
    texto = texto.casefold()
    return re.sub(r"\s+", " ", texto).strip()


def cargar_corpus():
    ruta = ROOT / CORPUS_PATH

    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el corpus: {ruta}")

    with ruta.open("r", encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames or []

        if "Abstract" not in columnas:
            raise ValueError(
                f"No existe columna Abstract. Columnas: {columnas}"
            )

        registros = list(lector)

    unicos = {}
    vacios = 0
    duplicados = 0

    for numero, registro in enumerate(registros, start=1):
        abstract = (registro.get("Abstract") or "").strip()

        if not abstract or normalizar(abstract) in {
            "nan", "none", "null", "no abstract"
        }:
            vacios += 1
            continue

        clave = normalizar(abstract)

        if clave in unicos:
            duplicados += 1
            unicos[clave]["filas_originales"].append(numero)
            continue

        unicos[clave] = {
            "id": f"OA3-{numero:04d}",
            "fila_original": numero,
            "filas_originales": [numero],
            "titulo": registro.get("Title", ""),
            "abstract": abstract,
        }

    resultado = list(unicos.values())

    print("=== AUDITORÍA DEL CORPUS OA3 ===")
    print(f"Registros originales: {len(registros)}")
    print(f"Sin abstract: {vacios}")
    print(f"Abstracts duplicados: {duplicados}")
    print(f"Abstracts únicos: {len(resultado)}")

    assert len(registros) == vacios + duplicados + len(resultado)

    return resultado


if __name__ == "__main__":
    cargar_corpus()
