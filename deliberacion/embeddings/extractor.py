import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

ORIGEN = BASE / "mallm/experiments/tambogrande/checkpoints/round2.json"
DESTINO = BASE / "embeddings/resultados/drafts_extraidos.json"

def extraer():
    with ORIGEN.open(encoding="utf-8") as f:
        datos = json.load(f)

    registros = [r for r in datos["globalMemory"] if r["turn"] == 1]

    if len(registros) != 8:
        raise ValueError("Se esperaban exactamente 8 agentes")

    resultado = []

    for r in registros:
        skos = r.get("additional_args", {}).get("skos", {})

        first = skos.get("first_draft_message", "")
        second = skos.get("second_draft_message", "")

        if not first.strip() or not second.strip():
            raise ValueError(f"Falta un draft: {r['persona']}")

        resultado.append({
            "agente": r["persona"],
            "first_draft": first,
            "second_draft": second
        })

    DESTINO.parent.mkdir(parents=True, exist_ok=True)

    with DESTINO.open("w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Extracción correcta: {len(resultado)} agentes")
    print(f"Archivo generado: {DESTINO}")

if __name__ == "__main__":
    extraer()
