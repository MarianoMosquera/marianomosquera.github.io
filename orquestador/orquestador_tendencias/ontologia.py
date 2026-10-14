"""Descarga y validación de la ontología SKOS desde GitHub main."""

import urllib.request
from rdflib import Graph

try:
    from .config import REPOSITORY, BRANCH, ONTOLOGY_FILES
except ImportError:
    from config import REPOSITORY, BRANCH, ONTOLOGY_FILES


def cargar_ontologia():
    grafo = Graph()

    if len(ONTOLOGY_FILES) != 11:
        raise RuntimeError("Se requieren exactamente 11 archivos TTL.")

    print("=== CARGA DE ONTOLOGÍA ===")

    for archivo in ONTOLOGY_FILES:
        url = (
            f"https://raw.githubusercontent.com/"
            f"{REPOSITORY}/{BRANCH}/{archivo}"
        )

        print(f"Descargando: {archivo}")

        solicitud = urllib.request.Request(
            url,
            headers={"User-Agent": "orquestador-tendencias"}
        )

        with urllib.request.urlopen(
            solicitud, timeout=30
        ) as respuesta:
            contenido = respuesta.read().decode("utf-8")

        grafo_archivo = Graph()
        grafo_archivo.parse(
            data=contenido,
            format="turtle",
            publicID=url
        )

        if len(grafo_archivo) == 0:
            raise RuntimeError(f"TTL vacío: {archivo}")

        grafo += grafo_archivo

        print(
            f"OK: {archivo} "
            f"({len(grafo_archivo)} triples)"
        )

    if len(grafo) == 0:
        raise RuntimeError("La ontología está vacía.")

    print(f"\nArchivos cargados: {len(ONTOLOGY_FILES)}")
    print(f"Triples RDF integrados: {len(grafo)}")

    return grafo


if __name__ == "__main__":
    cargar_ontologia()
