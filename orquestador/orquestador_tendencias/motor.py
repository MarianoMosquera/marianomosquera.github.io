"""Motor OA3: análisis individual contra el grafo RDF completo."""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI
from rdflib import Graph
from rdflib.compare import to_canonical_graph

from .config import MODEL, REASONING_EFFORT, MAX_OUTPUT_TOKENS, ONTOLOGY_FILES
from .corpus import cargar_corpus
from .ontologia import cargar_ontologia
from .prompt import SYSTEM_PROMPT

BASE = Path(__file__).resolve().parent
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "hallazgos": {
            "type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "concepto": {"type": "string"},
                    "tipo": {"type": "string", "enum": ["concepto", "dimension", "mecanismo", "relacion", "perspectiva"]},
                    "descripcion": {"type": "string"},
                    "evidencia_ingles": {"type": "string"},
                    "elementos_skos_examinados": {"type": "array", "items": {"type": "string"}},
                    "justificacion_no_subsuncion": {"type": "string"},
                },
                "required": ["concepto", "tipo", "descripcion", "evidencia_ingles", "elementos_skos_examinados", "justificacion_no_subsuncion"]
            }
        }
    }, "required": ["hallazgos"]
}


def guardar_json(ruta, contenido):
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ruta)


def analizar(cliente, registro, rdf):
    contenido = (
        "ONTOLOGÍA RDF COMPLETA (11 TTL integrados; marco semántico, NO diccionario):\n"
        + rdf + "\n\nABSTRACT (única fuente de evidencia):\n" + registro["abstract"]
    )
    ultima = None
    for intento in range(3):
        try:
            respuesta = cliente.responses.create(
                model=MODEL,
                reasoning={"effort": REASONING_EFFORT},
                max_output_tokens=MAX_OUTPUT_TOKENS,
                instructions=SYSTEM_PROMPT,
                input=contenido,
                prompt_cache_key="tendencias-oa3-" + hashlib.sha256(
                    (SYSTEM_PROMPT + rdf).encode("utf-8")
                ).hexdigest()[:24],
                text={"format": {"type": "json_schema", "name": "novedades_oa3", "strict": True, "schema": SCHEMA}},
            )
            if getattr(respuesta, "status", None) == "incomplete":
                raise RuntimeError("Respuesta incompleta: aumentar límite o revisar razonamiento")
            texto = respuesta.output_text
            if not texto:
                raise RuntimeError("Respuesta sin contenido estructurado")
            datos = json.loads(texto)
            for h in datos["hallazgos"]:
                evidencia = h["evidencia_ingles"].strip()
                if not evidencia or evidencia not in registro["abstract"]:
                    raise ValueError("La evidencia no es una cita literal del abstract")
                if not h["elementos_skos_examinados"] or not h["justificacion_no_subsuncion"].strip():
                    raise ValueError("Falta auditoría de subsunción")
            uso = getattr(respuesta, "usage", None)
            entrada = getattr(uso, "input_tokens", 0) or 0
            salida_tokens = getattr(uso, "output_tokens", 0) or 0
            detalles = getattr(uso, "input_tokens_details", None)
            cache = getattr(detalles, "cached_tokens", 0) or 0
            return datos, {
                "input_tokens": entrada,
                "cached_tokens": cache,
                "output_tokens": salida_tokens,
            }
        except (Exception) as exc:
            ultima = exc
            if intento < 2:
                time.sleep(2 ** intento)
    raise RuntimeError(f"Fallo tras tres intentos: {ultima}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="0: corpus completo")
    parser.add_argument("--offset", type=int, default=0, help="Abstracts iniciales que se omiten")
    parser.add_argument("--out", default=str(BASE / "resultados"))
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit no puede ser negativo")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Falta OPENAI_API_KEY; no se realizaron llamadas")
    registros = cargar_corpus()
    registros = registros[args.offset:]
    if args.limit:
        registros = registros[:args.limit]
    grafo = cargar_ontologia()
    # N-Triples conserva identificadores y relaciones explícitos, sin convertirlos en etiquetas.
    # Grafo canonizado: identificadores de nodos anónimos estables.
    # Turtle mantiene los triples RDF, compactando URIs con prefijos.
    rdf = to_canonical_graph(grafo).serialize(format="turtle")
    print(f"Contexto RDF Turtle: {len(rdf):,} caracteres", flush=True)
    huella = hashlib.sha256(rdf.encode("utf-8")).hexdigest()
    salida = Path(args.out)
    salida.mkdir(parents=True, exist_ok=True)
    cliente = OpenAI(timeout=180.0, max_retries=1)
    resultados = []
    errores = []
    consumo = []
    for numero, registro in enumerate(registros, 1):
        destino = salida / f'{registro["id"]}.json'
        if destino.exists():
            previo = json.loads(destino.read_text(encoding="utf-8"))
            if previo.get("ontology_sha256") == huella and previo.get("abstract_sha256") == hashlib.sha256(registro["abstract"].encode()).hexdigest() and previo.get("model") == MODEL:
                resultados.append(previo)
                print(f"[{numero}/{len(registros)}] Reutilizado: {registro['id']}", flush=True)
                continue
        try:
            datos, uso = analizar(cliente, registro, rdf)
            consumo.append({"id": registro["id"], **uso})
            print(f"Tokens {registro['id']}: entrada={uso['input_tokens']}, cache={uso['cached_tokens']}, salida={uso['output_tokens']}", flush=True)
            item = {
                "id": registro["id"], "titulo": registro["titulo"],
                "filas_originales": registro["filas_originales"],
                "abstract_sha256": hashlib.sha256(registro["abstract"].encode()).hexdigest(),
                "ontology_sha256": huella, "model": MODEL,
                "fecha_utc": datetime.now(timezone.utc).isoformat(),
                "hallazgos": datos["hallazgos"],
            }
            guardar_json(destino, item)
            resultados.append(item)
            print(f"[{numero}/{len(registros)}] {registro['id']}: {len(datos['hallazgos'])} hallazgos", flush=True)
        except Exception as exc:
            errores.append({"id": registro["id"], "error": str(exc)})
            print(f"ERROR {registro['id']}: {exc}", file=sys.stderr, flush=True)
    campos = ["id", "titulo", "concepto", "tipo", "descripcion", "evidencia_ingles", "elementos_skos_examinados", "justificacion_no_subsuncion"]
    with (salida / "hallazgos.csv").open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for item in resultados:
            for h in item["hallazgos"]:
                escritor.writerow({"id": item["id"], "titulo": item["titulo"], **{k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v for k, v in h.items()}})
    conteo = Counter(h["tipo"] for item in resultados for h in item["hallazgos"])
    resumen = {
        "registros_seleccionados": len(registros), "procesados": len(resultados),
        "errores": errores, "hallazgos_total": sum(conteo.values()),
        "por_tipo": dict(conteo), "ontology_sha256": huella,
        "ttl": ONTOLOGY_FILES, "triples": len(grafo), "modelo": MODEL,
        "consumo_tokens": consumo,
        "tokens_entrada_total": sum(x["input_tokens"] for x in consumo),
        "tokens_cache_total": sum(x["cached_tokens"] for x in consumo),
        "tokens_salida_total": sum(x["output_tokens"] for x in consumo),
        "nota": "Frecuencias descriptivas; no constituyen prueba estadística de asociación SKOS."
    }
    guardar_json(salida / "resumen.json", resumen)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    if errores:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
