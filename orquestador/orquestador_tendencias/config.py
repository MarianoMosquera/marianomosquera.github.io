"""Configuración del orquestador de tendencias ontológicas."""

REPOSITORY = "MarianoMosquera/marianomosquera.github.io"
BRANCH = "main"

CORPUS_PATH = "corpus/OA3_2026_En.csv"

ONTOLOGY_FILES = [
    "valores.ttl",
    "accountability.ttl",
    "engagement.ttl",
    "racionalidad.ttl",
    "compliance.ttl",
    "social.ttl",
    "institucional.ttl",
    "ambiental.ttl",
    "economica.ttl",
    "tecnologica.ttl",
    "politica.ttl",
]

assert len(ONTOLOGY_FILES) == 11
assert len(set(ONTOLOGY_FILES)) == 11

MODEL = "gpt-6-astra"
REASONING_EFFORT = "high"
MAX_OUTPUT_TOKENS = 12000
