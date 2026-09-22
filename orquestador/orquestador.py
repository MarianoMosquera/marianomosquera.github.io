#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ORQUESTADOR DE ANÁLISIS SEMÁNTICO DE ABSTRACTS
Proyecto: Ética Institucional y Transparencia

Flujo:
1 abstract
→ 1 unidad independiente de análisis
→ Batch API
→ Prompt Caching (instrucciones + SKOS)
→ GPT-6 Astra con reasoning=max
→ Structured Outputs
→ validación
→ transformación Python
→ 76 campos
→ Base estadística CSV/XLSX
→ Corpus anotado CSV

IMPORTANTE
----------
- OPENAI_API_KEY se obtiene exclusivamente de una variable de entorno.
- Nunca escribir la API key en este archivo.
- Los 11 SKOS se leen desde la raíz del repositorio.
- Cada abstract se envía como una solicitud independiente.
- El abstract es el único contenido sustantivo del corpus enviado al modelo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

MODEL = os.getenv("OPENAI_MODEL", "gpt-6-astra")
REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "max")

BATCH_ENDPOINT = "/v1/responses"
BATCH_COMPLETION_WINDOW = "24h"

MAX_OUTPUT_TOKENS = 12000

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

CORPUS_PATH = REPO_ROOT / "corpus" / "OA_2026_Es.csv"

OUTPUT_DIR = REPO_ROOT / "resultados"

BATCH_INPUT_PATH = OUTPUT_DIR / "batch_input.jsonl"
BATCH_RAW_OUTPUT_PATH = OUTPUT_DIR / "batch_output_raw.jsonl"
BATCH_RAW_ERROR_PATH = OUTPUT_DIR / "batch_errors_raw.jsonl"
BATCH_STATE_PATH = OUTPUT_DIR / "batch_state.json"

STATISTICAL_CSV_PATH = OUTPUT_DIR / "base_estadistica_76_columnas.csv"
STATISTICAL_XLSX_PATH = OUTPUT_DIR / "base_estadistica_76_columnas.xlsx"
ANNOTATED_CSV_PATH = OUTPUT_DIR / "corpus_anotado.csv"
VALIDATION_REPORT_PATH = OUTPUT_DIR / "reporte_validacion.csv"
EXCLUDED_REPORT_PATH = OUTPUT_DIR / "registros_sin_abstract.csv"

SKOS_FILES = [
    "valores.ttl",
    "politica.ttl",
    "economica.ttl",
    "social.ttl",
    "tecnologica.ttl",
    "ambiental.ttl",
    "institucional.ttl",
    "racionalidad.ttl",
    "compliance.ttl",
    "accountability.ttl",
    "engagement.ttl",
]


# ============================================================
# 2. DEFINICIÓN DE LAS 27 CATEGORÍAS
# ============================================================

CATEGORIES: List[Tuple[str, str, bool]] = [

    # VALORES
    ("Cooperación", "Valores", False),
    ("Igualdad", "Valores", False),
    ("Justicia", "Valores", False),
    ("Competencia", "Valores", False),
    ("Libertad", "Valores", False),
    ("Propiedad", "Valores", False),

    # AGENDA
    ("Política", "Agenda", True),
    ("Económica", "Agenda", True),
    ("Social", "Agenda", True),
    ("Tecnológica", "Agenda", True),
    ("Ambiental", "Agenda", True),
    ("Institucional", "Agenda", True),

    # RACIONALIDAD
    ("Teoría", "Racionalidad", True),
    ("Teleología", "Racionalidad", True),
    ("Evidencia", "Racionalidad", True),

    # COMPLIANCE
    ("Responsabilidad", "Compliance", True),
    ("Análisis_de_riesgo", "Compliance", True),
    ("Normas", "Compliance", True),
    ("Compliance_Problemas", "Compliance", True),

    # ACCOUNTABILITY
    ("Transparencia", "Accountability", True),
    ("Control", "Accountability", True),
    ("Sanción", "Accountability", True),
    ("Actores", "Accountability", True),
    ("Accountability_Problemas", "Accountability", True),

    # ENGAGEMENT
    ("Anticipación", "Engagement", True),
    ("Colaboración", "Engagement", True),
    ("Engagement_Problemas", "Engagement", True),
]

assert len(CATEGORIES) == 27


# ============================================================
# 3. INSTRUCCIONES SEMÁNTICAS DEL MODELO
# ============================================================

MODEL_INSTRUCTIONS = r"""
INSTRUCCIONES PARA EL ANÁLISIS SEMÁNTICO Y ONTOLÓGICAMENTE GUIADO

OBJETIVO

Analizar UN ÚNICO abstract como unidad completamente independiente.

Debes determinar la presencia o ausencia de 27 categorías conceptuales
utilizando las ontologías SKOS proporcionadas como vocabulario conceptual,
estructura jerárquica y marco semántico de referencia.

El análisis debe ser contextual, semántico y ontológicamente guiado.

NO debe reducirse:
- a coincidencias literales de palabras;
- a búsqueda de keywords;
- al reconocimiento aislado de entidades;
- ni a propagación automática de categorías por relaciones jerárquicas.

Debes analizar exclusivamente el abstract suministrado.

No utilices conocimiento externo para inventar evidencia.

Toda evidencia registrada debe aparecer efectivamente en el abstract.


============================================================
CATEGORÍAS
============================================================

VALORES
1. Cooperación
2. Igualdad
3. Justicia
4. Competencia
5. Libertad
6. Propiedad

AGENDA
7. Política
8. Económica
9. Social
10. Tecnológica
11. Ambiental
12. Institucional

RACIONALIDAD
13. Teoría
14. Teleología
15. Evidencia

COMPLIANCE
16. Responsabilidad
17. Análisis_de_riesgo
18. Normas
19. Compliance_Problemas

ACCOUNTABILITY
20. Transparencia
21. Control
22. Sanción
23. Actores
24. Accountability_Problemas

ENGAGEMENT
25. Anticipación
26. Colaboración
27. Engagement_Problemas


============================================================
CLASIFICACIÓN BINARIA
============================================================

Para cada categoría:

1 = existe evidencia contextual suficiente de que la categoría está presente
en el contenido sustantivo del abstract.

0 = no existe evidencia contextual suficiente para considerar presente
la categoría.

La presencia de una categoría se computa una sola vez por abstract,
independientemente del número de términos, expresiones o entidades
que la sustenten.

Varias evidencias para una misma categoría continúan produciendo un único 1.

El valor 1 puede estar sustentado:
- por evidencia semántica;
- por entidades concretas;
- o por ambas.

Cada categoría debe evaluarse independientemente.

La presencia de una categoría NO debe inferirse automáticamente
de la presencia de otra categoría.

Las relaciones jerárquicas, semánticas o conceptuales entre categorías
no son suficientes por sí solas para propagar una clasificación positiva.

Cada valor 1 debe contar con evidencia contextual suficiente,
trazable y justificable de manera independiente.


============================================================
CRITERIO GENERAL DE PRESENCIA
============================================================

Una categoría recibe valor 1 únicamente cuando exista evidencia contextual
suficiente de su presencia en el objeto sustantivo estudiado por el abstract.

La presencia puede determinarse mediante:

- mención explícita de un concepto incluido en el SKOS;
- término o expresión semánticamente equivalente;
- término o expresión conceptualmente próxima;
- expresión relacionada contextualmente con la estructura conceptual SKOS;
- concepto emergente todavía no incorporado al SKOS pero claramente
  relacionado con la categoría;
- entidad concreta cuya función o significado dentro del abstract
  constituya evidencia específica de la categoría.

El SKOS es un marco conceptual de referencia.
NO es una lista cerrada de palabras.

Debes considerar conjuntamente:

- significado de la expresión;
- contexto;
- relaciones ontológicas SKOS;
- objeto sustantivo del abstract.

ORDEN LÓGICO OBLIGATORIO:

1. Identificar posible evidencia presente en el abstract.
2. Determinar si pertenece al objeto sustantivo estudiado.
3. Desambiguar su significado contextual.
4. Evaluar su correspondencia con las categorías y los SKOS.
5. Sólo entonces asignar 0 o 1.

NO debes asignar primero una categoría y buscar posteriormente evidencia
destinada a justificarla.


============================================================
EVIDENCIA SEMÁNTICA
============================================================

Para cada categoría existe un campo "sem".

Cuando exista evidencia semántica, registrar exclusivamente los términos
o expresiones DEL ABSTRACT que justifican conceptualmente la clasificación.

Puede contener:

- términos explícitamente incluidos en el SKOS;
- equivalencias o aproximaciones semánticas;
- expresiones conceptualmente relacionadas con la ontología;
- conceptos emergentes relevantes no incorporados todavía al SKOS.

Debes registrar TODOS los términos o expresiones relevantes del abstract
que efectivamente justifican la categoría.

Mantener, siempre que sea posible, la expresión textual original
utilizada en el abstract.

Separar múltiples elementos mediante punto y coma.

Las entidades concretas no deben registrarse como evidencia semántica,
salvo que la expresión funcione inequívocamente como concepto
y no como entidad.

Si una categoría obtiene 1 exclusivamente por evidencia de entidad,
"sem" debe ser cadena vacía.


============================================================
ENTIDADES
============================================================

Las seis categorías de Valores NO admiten entidades.

Las restantes 21 categorías poseen un campo "ent".

Registrar exclusivamente entidades efectivamente mencionadas en el abstract
que aporten evidencia contextual a la categoría correspondiente.

Pueden considerarse:

- instituciones y organismos;
- organizaciones públicas, privadas o de sociedad civil;
- programas e iniciativas identificables;
- políticas específicas;
- leyes;
- tratados;
- códigos;
- normas;
- instrumentos identificables;
- personas;
- actores colectivos identificables;
- otras entidades nombradas que aporten evidencia sustantiva.

La mera aparición de una entidad NO constituye automáticamente
evidencia de una categoría.

La entidad debe desempeñar dentro del abstract una función
semánticamente pertinente para esa categoría.

Una misma entidad puede constituir evidencia de más de una categoría
únicamente de forma excepcional, cuando el contexto permita justificar
independientemente cada clasificación.

Si no existen entidades relevantes, "ent" debe ser cadena vacía,
aunque la categoría tenga valor 1 por evidencia semántica.


============================================================
RELACIÓN ENTRE CLASIFICACIÓN Y EVIDENCIA
============================================================

Si presencia = 0:
- sem debe ser "";
- ent debe ser "" cuando exista ese campo.

Si presencia = 1:
- debe existir evidencia trazable en sem, ent o ambas.

Nunca asignar 1 sin evidencia explícitamente identificable en el abstract.

La evidencia debe corresponder específicamente a la categoría
que pretende justificar.

La evidencia precede lógicamente a la clasificación.


============================================================
DESAMBIGUACIÓN OBLIGATORIA
============================================================

Debes resolver dos tipos de desambiguación:

1. DESAMBIGUACIÓN EXTERNA:
distinguir el objeto sustantivo estudiado por el abstract de los métodos,
datos, procedimientos o decisiones utilizados por los autores
para realizar la investigación.

2. DESAMBIGUACIÓN INTERNA:
determinar a qué categoría corresponde una evidencia cuando un término,
expresión o entidad puede relacionarse con varias categorías.


============================================================
OBJETO DE ESTUDIO VS. METODOLOGÍA DEL ARTÍCULO
============================================================

La clasificación debe referirse al fenómeno, institución, práctica,
política, proceso o problema que constituye el objeto sustantivo del abstract.

NO clasificar automáticamente como categorías del objeto de estudio
los elementos utilizados exclusivamente por los autores para desarrollar
su investigación.

Esto incluye:

- métodos de investigación;
- fuentes de datos;
- técnicas estadísticas;
- procedimientos de análisis;
- evidencia utilizada por los investigadores;
- decisiones metodológicas;
- procedimientos de ética de investigación aplicados al propio estudio.

Pregunta de control:

¿Este elemento pertenece al fenómeno estudiado o solamente al procedimiento
mediante el cual los autores lo investigaron?

Si pertenece únicamente al procedimiento de investigación,
NO debe utilizarse para clasificar el objeto sustantivo.


============================================================
RACIONALIDAD: EVIDENCIA VS. EVIDENCIA PARA CLASIFICAR
============================================================

Distinguir:

A) Evidencia como categoría de Racionalidad:
cuando la producción, utilización, evaluación, calidad o consideración
de evidencia forma parte del objeto sustantivo estudiado.

B) Evidencia utilizada para justificar cualquier clasificación:
término, expresión o entidad utilizada para determinar la presencia
de otra categoría.

B NO implica A.


============================================================
ÉTICA EN INVESTIGACIÓN
============================================================

Las referencias a:

- aprobación ética;
- consentimiento;
- comités de ética;
- requisitos éticos aplicados por los autores;

NO deben clasificarse como parte del objeto sustantivo cuando correspondan
solamente al procedimiento de la propia investigación.

Sólo deben considerarse cuando la ética en investigación sea ella misma
objeto, práctica, política, institución, regulación o fenómeno
analizado por el abstract.


============================================================
COMPLIANCE_NORMAS VS. INSTITUCIONAL
============================================================

La presencia de una ley, regulación, norma o marco normativo
NO implica automáticamente Normas = 1.

Clasificar las normas según la función que cumplen en el contexto
y según el significado establecido por cada SKOS.

Las referencias generales a:

- leyes;
- regulación;
- marcos jurídicos;
- convenciones;
- estructuras normativas;

corresponden a Institucional cuando son tratadas como componentes
generales del marco institucional.

Normas de Compliance debe utilizarse únicamente cuando la norma corresponda
específicamente al sentido definido por el SKOS de Compliance.

Clasificar por FUNCIÓN SEMÁNTICA, no por la mera presencia de palabras
como law, regulation, code, rule o equivalentes.


============================================================
NORMAS VS. MECANISMOS ESPECÍFICOS DE ACCOUNTABILITY
============================================================

Una norma, procedimiento o instrumento vinculado específicamente con:

- Transparencia;
- Control;
- Sanción;

debe analizarse primero según la función concreta que cumple.

Si funciona sustantivamente como mecanismo de transparencia,
control o sanción, clasificarlo en la categoría correspondiente
de Accountability.

NO asignarlo adicionalmente a Compliance Normas por el solo hecho
de poseer naturaleza normativa.

Las normas generales, cuando correspondan al marco jurídico o institucional
sin una función específica definida por Compliance o Accountability,
deben clasificarse como Institucional.


============================================================
ACTORES VS. ENTIDADES
============================================================

Distinguir entre:

- una entidad mencionada;
- la categoría conceptual Actores.

Que una institución, organización, persona o colectivo aparezca en "ent"
NO significa automáticamente que deba activarse Actores.

Una entidad será evidencia de Accountability_Actores únicamente cuando
desempeñe una función correspondiente al concepto de Actores definido
por el SKOS de Accountability.

De igual manera, una entidad podrá constituir evidencia de Engagement
u otra categoría únicamente cuando su función contextual corresponda
específicamente a esa ontología.

Entidad nombrada ≠ categoría Actores.


============================================================
PROBLEMAS
============================================================

Los problemas deben clasificarse según:

- el fenómeno específico que representan;
- la función que cumplen dentro del objeto estudiado.

Los problemas políticos, económicos, sociales, tecnológicos,
ambientales o institucionales deben corresponder a esas categorías
cuando el problema pertenezca sustantivamente a ese dominio.

Compliance_Problemas,
Accountability_Problemas y
Engagement_Problemas

deben utilizarse únicamente cuando el problema corresponda específicamente
al significado definido por sus respectivos SKOS.

La mera condición negativa, problemática o crítica de un fenómeno
NO es suficiente para activar una categoría Problemas.


============================================================
RACIONALIDAD: LENGUAJE ORDINARIO VS. ESTRUCTURA TELEOLÓGICA
============================================================

La presencia de términos o expresiones coincidentes con conceptos
del SKOS de Racionalidad, por ejemplo:

- Problema–Solución;
- Alternativas–Preferencias;
- Costo–Beneficio;

u otros conceptos subordinados,

NO implica automáticamente Teleología = 1.

Sólo clasificarlos como evidencia de Teleología cuando,
dentro del objeto sustantivo estudiado,
expresen efectivamente la estructura o función conceptual
definida por el SKOS.

El uso como lenguaje ordinario, descriptivo o incidental
NO es suficiente.


============================================================
RELACIÓN JERÁRQUICA SKOS VS. ACTIVACIÓN
============================================================

La relación jerárquica definida por el SKOS orienta la interpretación
semántica, pero NO sustituye la evaluación contextual.

La presencia de un concepto subordinado (narrower) puede constituir
evidencia de la categoría superior únicamente cuando el término
o expresión conserve, en el contexto del abstract,
el significado definido por el SKOS.

Una coincidencia léxica con un concepto subordinado NO debe activar
automáticamente la categoría superior cuando el término sea utilizado
con otro significado o función contextual.


============================================================
UNA MISMA EVIDENCIA Y MÚLTIPLES CATEGORÍAS
============================================================

Un mismo término, expresión o entidad puede justificar más de una categoría
únicamente y excepcionalmente cuando el contexto permita establecer
de manera independiente la presencia de cada una.

NO multiplicar categorías por asociación automática.

Para cada categoría debe existir una justificación semántica autónoma
basada en el abstract y en su SKOS correspondiente.

La coincidencia de una misma evidencia en varias categorías sólo es válida
cuando exista verdadera superposición conceptual en el fenómeno estudiado.


============================================================
SECUENCIA FINAL DE DESAMBIGUACIÓN
============================================================

ANTES de asignar 1 verificar sucesivamente:

1. EXISTENCIA
¿La evidencia semántica y/o entidad aparece efectivamente en el abstract?

2. SUSTANTIVIDAD
¿Pertenece al objeto sustantivo estudiado y no solamente al método
utilizado por los autores?

3. PERTINENCIA ONTOLÓGICA
¿El significado contextual corresponde a la categoría según su SKOS?

4. ESPECIFICIDAD
¿Existe otra categoría cuya definición explique de manera más significativa
esa evidencia?

5. INDEPENDENCIA
Si puede corresponder a varias categorías,
¿existe evidencia contextual suficiente para justificar cada clasificación
de manera independiente?

6. CONSERVADURISMO
Si persiste una ambigüedad relevante que impide establecer evidencia
contextual suficiente y trazable, asignar 0.

Una coincidencia léxica, similitud superficial o mera aparición
de una entidad nunca son suficientes.

Ante ambigüedad no resuelta:
asignar 1 únicamente cuando exista evidencia contextual suficiente
y trazable.


============================================================
REGLAS DE REGISTRO
============================================================

- Registrar únicamente términos, expresiones y entidades efectivamente
  presentes en el abstract.

- No inventar evidencia.

- No completar evidencia implícita que no aparezca en el texto.

- No duplicar un mismo elemento dentro de una misma categoría.

- Mantener siempre que sea posible la expresión original del abstract.

- Separar múltiples elementos mediante punto y coma.

- No incluir explicaciones, razonamientos ni comentarios en sem o ent.

- No registrar como entidad un concepto genérico que corresponda
  propiamente a evidencia semántica.

- No registrar como evidencia semántica una entidad únicamente para
  justificar artificialmente una clasificación.

- No inferir ni forzar entidades.

- Una entidad válida puede constituir por sí misma evidencia suficiente
  para asignar 1 cuando su función contextual corresponda inequívocamente
  a la categoría.

- Toda evidencia debe registrarse únicamente en las categorías
  para las que resulte contextualmente pertinente.


============================================================
PRINCIPIO GENERAL
============================================================

Integrar:

- vocabulario explícito contenido en los SKOS;
- relaciones jerárquicas y semánticas SKOS;
- equivalencia semántica contextual;
- similitud semántica contextual;
- reconocimiento contextual de entidades;
- identificación de conceptos emergentes;
- función contextual de términos y entidades;
- reglas de desambiguación externa e interna.

El objetivo NO es realizar búsqueda de palabras.

El objetivo es realizar clasificación semántica,
contextual y ontológicamente guiada.

Todo valor 1 debe vincularse directamente con evidencia registrada
en sem y/o ent.

Analizar cada categoría independientemente.

Evitar cualquier propagación automática entre categorías relacionadas.
"""


# ============================================================
# 4. UTILIDADES
# ============================================================

def fatal(message: str) -> None:
    print(f"\nERROR: {message}\n", file=sys.stderr)
    sys.exit(1)


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        fatal(
            "No se encontró OPENAI_API_KEY. "
            "Debe estar configurada como variable de entorno "
            "o GitHub Secret."
        )

    return api_key


def sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ============================================================
# 5. CARGA DE LOS 11 SKOS DESDE MAIN
# ============================================================

def load_skos() -> str:

    sections: List[str] = []

    for filename in SKOS_FILES:

        path = REPO_ROOT / filename

        if not path.exists():
            fatal(
                f"No se encontró el SKOS requerido: {path}\n"
                f"Debe existir en la raíz/main del repositorio."
            )

        text = path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            fatal(
                f"El archivo SKOS está vacío: {filename}"
            )

        sections.append(
            "\n\n"
            "============================================================\n"
            f"SKOS: {filename}\n"
            "============================================================\n"
            f"{text}"
        )

    combined = "".join(sections)

    info(
        f"SKOS cargados correctamente: "
        f"{len(SKOS_FILES)}"
    )

    info(
        f"Hash conjunto SKOS: "
        f"{sha256_text(combined)[:16]}"
    )

    return combined


# ============================================================
# 6. LECTURA DEL CORPUS
# ============================================================

ABSTRACT_COLUMN_CANDIDATES = {
    "abstract",
    "abstracts",
    "abstract text",
    "abstract_text",
    "resumen",
}


def normalize_header(value: str) -> str:
    return str(value).strip().lower()


def detect_abstract_column(
    df: pd.DataFrame
) -> str:

    normalized = {
        normalize_header(column): column
        for column in df.columns
    }

    for candidate in ABSTRACT_COLUMN_CANDIDATES:

        if candidate in normalized:
            return normalized[candidate]

    matches = [
        column
        for column in df.columns
        if "abstract" in normalize_header(column)
    ]

    if len(matches) == 1:
        return matches[0]

    fatal(
        "No fue posible identificar de manera inequívoca "
        "la columna Abstract.\n"
        f"Columnas disponibles: {list(df.columns)}"
    )

    raise RuntimeError


def read_csv_robust(
    path: Path
) -> pd.DataFrame:

    if not path.exists():
        fatal(
            f"No se encontró el corpus: {path}"
        )

    encodings = [
        "utf-8-sig",
        "utf-8",
        "latin-1",
    ]

    last_error: Optional[Exception] = None

    for encoding in encodings:

        try:

            df = pd.read_csv(
                path,
                sep=None,
                engine="python",
                encoding=encoding,
                dtype=str,
                keep_default_na=False,
            )

            info(
                f"Corpus leído con encoding: "
                f"{encoding}"
            )

            return df

        except Exception as exc:
            last_error = exc

    fatal(
        f"No se pudo leer el CSV. "
        f"Último error: {last_error}"
    )

    raise RuntimeError


def load_corpus(
    limit: Optional[int] = None
) -> Tuple[
    pd.DataFrame,
    str,
    pd.DataFrame
]:

    """
    Lee el corpus y selecciona exclusivamente registros
    que contienen abstract.

    Si se especifica limit, se seleccionan solamente los
    primeros N abstracts válidos.

    Ejemplo:
        limit=40

    Los ID se generan DESPUÉS de excluir registros sin abstract
    y DESPUÉS de aplicar el límite.

    Para la prueba de 40:
        00001 ... 00040
    """

    df = read_csv_robust(
        CORPUS_PATH
    )

    abstract_column = detect_abstract_column(
        df
    )

    info(
        f"Columna de abstract detectada: "
        f"{abstract_column}"
    )

    abstracts = (
        df[abstract_column]
        .astype(str)
        .str.strip()
    )

    valid_mask = abstracts.ne("")

    excluded = (
        df.loc[~valid_mask]
        .copy()
    )

    valid = (
        df.loc[valid_mask]
        .copy()
        .reset_index(drop=True)
    )

    total_valid_before_limit = len(valid)

    # --------------------------------------------------------
    # LÍMITE OPCIONAL PARA PRUEBAS
    # --------------------------------------------------------

    if limit is not None:

        if limit <= 0:
            fatal(
                "El límite debe ser un número entero "
                "mayor que 0."
            )

        valid = (
            valid.head(limit)
            .copy()
            .reset_index(drop=True)
        )

        info(
            "Modo de prueba activado: "
            f"máximo {limit} abstracts."
        )

    # --------------------------------------------------------
    # ID CORRELATIVO
    # --------------------------------------------------------

    valid["ID"] = [
        f"{i:05d}"
        for i in range(
            1,
            len(valid) + 1
        )
    ]

    valid["__ABSTRACT__"] = (
        valid[abstract_column]
        .astype(str)
        .str.strip()
    )

    if valid["ID"].duplicated().any():
        fatal(
            "Se detectaron ID duplicados."
        )

    if valid["__ABSTRACT__"].eq("").any():
        fatal(
            "Persisten abstracts vacíos "
            "después del filtrado."
        )

    info(
        f"Registros totales del CSV: "
        f"{len(df)}"
    )

    info(
        f"Abstracts válidos disponibles: "
        f"{total_valid_before_limit}"
    )

    info(
        f"Abstracts seleccionados para esta ejecución: "
        f"{len(valid)}"
    )

    info(
        f"Registros sin abstract: "
        f"{len(excluded)}"
    )

    return (
        valid,
        abstract_column,
        excluded,
    )


# ============================================================
# 7. JSON SCHEMA
# ============================================================

def category_schema(
    has_entities: bool
) -> Dict[str, Any]:

    properties: Dict[str, Any] = {

        "presencia": {
            "type": "integer",
            "enum": [0, 1],
            "description": (
                "1 si existe evidencia contextual suficiente "
                "y trazable de la categoría; "
                "0 en caso contrario."
            ),
        },

        "sem": {
            "type": "string",
            "description": (
                "Términos o expresiones efectivamente presentes "
                "en el abstract que constituyen evidencia semántica. "
                "Separar mediante punto y coma. "
                "Cadena vacía si no existe evidencia semántica."
            ),
        },
    }

    required = [
        "presencia",
        "sem",
    ]

    if has_entities:

        properties["ent"] = {
            "type": "string",
            "description": (
                "Entidades efectivamente mencionadas en el abstract "
                "que constituyen evidencia contextual de la categoría. "
                "Separar mediante punto y coma. "
                "Cadena vacía si no existen entidades pertinentes."
            ),
        }

        required.append("ent")

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def build_json_schema() -> Dict[str, Any]:

    category_properties: Dict[str, Any] = {}

    for (
        category,
        _,
        has_entities,
    ) in CATEGORIES:

        category_properties[
            category
        ] = category_schema(
            has_entities
        )

    return {

        "type": "object",

        "properties": {

            "id": {
                "type": "string",
                "pattern": r"^\d{5}$",
            },

            "categorias": {

                "type": "object",

                "properties":
                    category_properties,

                "required": [
                    category
                    for (
                        category,
                        _,
                        _
                    ) in CATEGORIES
                ],

                "additionalProperties":
                    False,
            },
        },

        "required": [
            "id",
            "categorias",
        ],

        "additionalProperties":
            False,
    }


OUTPUT_SCHEMA = build_json_schema()


# ============================================================
# 8. PREFIJO ESTABLE PARA PROMPT CACHING
# ============================================================

def build_stable_prompt(
    skos_text: str
) -> str:

    return (

        MODEL_INSTRUCTIONS.strip()

        + "\n\n\n"

        + "============================================================\n"
        + "ONTOLOGÍAS SKOS DE REFERENCIA\n"
        + "============================================================\n"

        + "\nLas siguientes ontologías constituyen "
          "el marco conceptual de referencia obligatorio.\n"

        + skos_text

        + "\n\n"

        + "============================================================\n"
        + "FIN DEL PREFIJO ESTABLE\n"
        + "============================================================\n"
    )


# ============================================================
# 9. REQUEST INDIVIDUAL
# ============================================================

def build_request(
    record_id: str,
    abstract: str,
    stable_prompt: str,
) -> Dict[str, Any]:

    user_text = (

        f"ID DEL ABSTRACT: "
        f"{record_id}\n\n"

        f"ABSTRACT:\n"
        f"{abstract}\n\n"

        "Analiza exclusivamente este abstract siguiendo "
        "estrictamente las instrucciones y ontologías proporcionadas. "
        "Devuelve únicamente la estructura definida "
        "por el JSON Schema."
    )

    body: Dict[str, Any] = {

        "model": MODEL,

        "reasoning": {
            "effort":
                REASONING_EFFORT
        },

        "max_output_tokens":
            MAX_OUTPUT_TOKENS,

        "prompt_cache_options": {
            "mode": "explicit",
            "ttl": "30m",
        },

        "input": [

            {
                "role": "developer",

                "content": [

                    {
                        "type": "input_text",

                        "text":
                            stable_prompt,

                        "prompt_cache_breakpoint": {
                            "mode":
                                "explicit"
                        },
                    }
                ],
            },

            {
                "role": "user",

                "content": [

                    {
                        "type":
                            "input_text",

                        "text":
                            user_text,
                    }
                ],
            },
        ],

        "text": {

            "format": {

                "type":
                    "json_schema",

                "name":
                    "clasificacion_abstract",

                "strict":
                    True,

                "schema":
                    OUTPUT_SCHEMA,
            }
        },
    }

    return {

        "custom_id":
            record_id,

        "method":
            "POST",

        "url":
            BATCH_ENDPOINT,

        "body":
            body,
    }


# ============================================================
# 10. PREPARACIÓN DEL BATCH
# ============================================================

def prepare_batch(
    limit: Optional[int] = None
) -> Dict[str, Any]:

    ensure_output_dir()

    skos_text = load_skos()

    stable_prompt = build_stable_prompt(
        skos_text
    )

    corpus, abstract_column, excluded = (
        load_corpus(
            limit=limit
        )
    )

    if len(corpus) == 0:
        fatal(
            "No existen abstracts para procesar."
        )

    if len(excluded) > 0:

        excluded.to_csv(
            EXCLUDED_REPORT_PATH,
            index=False,
            encoding="utf-8-sig",
        )

    with BATCH_INPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:

        for _, row in corpus.iterrows():

            request = build_request(

                record_id=
                    row["ID"],

                abstract=
                    row["__ABSTRACT__"],

                stable_prompt=
                    stable_prompt,
            )

            handle.write(

                json.dumps(
                    request,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

                + "\n"
            )

    state = {

        "model":
            MODEL,

        "reasoning_effort":
            REASONING_EFFORT,

        "corpus_path":
            str(CORPUS_PATH),

        "abstract_column":
            abstract_column,

        "limit":
            limit,

        "number_of_abstracts":
            len(corpus),

        "number_excluded_without_abstract":
            len(excluded),

        "skos_files":
            SKOS_FILES,

        "skos_hash":
            sha256_text(
                skos_text
            ),

        "stable_prompt_hash":
            sha256_text(
                stable_prompt
            ),

        "batch_input_path":
            str(BATCH_INPUT_PATH),

        "batch_id":
            None,

        "input_file_id":
            None,

        "output_file_id":
            None,

        "error_file_id":
            None,

        "status":
            "prepared",
    }

    save_state(
        state
    )

    info(
        f"Batch preparado: "
        f"{BATCH_INPUT_PATH}"
    )

    info(
        f"Solicitudes creadas: "
        f"{len(corpus)}"
    )

    info(
        "NO se ha enviado todavía "
        "nada a OpenAI."
    )

    return state


# ============================================================
# 11. ESTADO LOCAL
# ============================================================

def save_state(
    state: Dict[str, Any]
) -> None:

    ensure_output_dir()

    BATCH_STATE_PATH.write_text(

        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),

        encoding="utf-8",
    )


def load_state() -> Dict[str, Any]:

    if not BATCH_STATE_PATH.exists():

        fatal(
            "No existe batch_state.json. "
            "Ejecute primero prepare."
        )

    return json.loads(

        BATCH_STATE_PATH.read_text(
            encoding="utf-8"
        )
    )


# ============================================================
# 12. CLIENTE OPENAI
# ============================================================

def get_openai_client():

    get_api_key()

    try:
        from openai import OpenAI

    except ImportError:

        fatal(
            "No está instalado el paquete openai."
        )

    return OpenAI()


# ============================================================
# 13. ENVÍO DEL BATCH
# ============================================================

def submit_batch() -> Dict[str, Any]:

    state = load_state()

    if state.get("batch_id"):

        fatal(
            "Este batch_state.json ya contiene "
            "un batch_id. "
            "No se enviará nuevamente para evitar "
            "duplicar costos."
        )

    if not BATCH_INPUT_PATH.exists():

        fatal(
            "No existe batch_input.jsonl. "
            "Ejecute primero prepare."
        )

    client = get_openai_client()

    info(
        "Subiendo batch_input.jsonl "
        "a OpenAI..."
    )

    with BATCH_INPUT_PATH.open(
        "rb"
    ) as handle:

        uploaded = client.files.create(
            file=handle,
            purpose="batch",
        )

    input_file_id = uploaded.id

    info(
        f"Archivo Batch cargado. "
        f"File ID: {input_file_id}"
    )

    info(
        "Creando Batch API..."
    )

    batch = client.batches.create(

        input_file_id=
            input_file_id,

        endpoint=
            BATCH_ENDPOINT,

        completion_window=
            BATCH_COMPLETION_WINDOW,

        metadata={
            "project":
                "etica_institucional_transparencia",

            "analysis":
                "abstract_semantic_classification",

            "model":
                MODEL,
        },
    )

    state["input_file_id"] = (
        input_file_id
    )

    state["batch_id"] = (
        batch.id
    )

    state["status"] = (
        batch.status
    )

    save_state(
        state
    )

    info(
        f"Batch creado: "
        f"{batch.id}"
    )

    info(
        f"Estado inicial: "
        f"{batch.status}"
    )

    return state


# ============================================================
# 14. CONSULTA DE ESTADO
# ============================================================

def check_status() -> Dict[str, Any]:

    state = load_state()

    batch_id = (
        os.getenv("OPENAI_BATCH_ID")
        or state.get("batch_id")
    )

    if not batch_id:
        fatal(
            "No existe batch_id."
        )

    client = get_openai_client()

    batch = client.batches.retrieve(
        batch_id
    )

    state["batch_id"] = batch.id

    state["status"] = batch.status

    state["output_file_id"] = getattr(
        batch,
        "output_file_id",
        None,
    )

    state["error_file_id"] = getattr(
        batch,
        "error_file_id",
        None,
    )

    request_counts = getattr(
        batch,
        "request_counts",
        None,
    )

    if request_counts is not None:

        state["request_counts"] = {

            "total":
                getattr(
                    request_counts,
                    "total",
                    None,
                ),

            "completed":
                getattr(
                    request_counts,
                    "completed",
                    None,
                ),

            "failed":
                getattr(
                    request_counts,
                    "failed",
                    None,
                ),
        }

    save_state(
        state
    )

    info(
        f"Batch: "
        f"{batch.id}"
    )

    info(
        f"Estado: "
        f"{batch.status}"
    )

    if request_counts is not None:

        info(
            "Solicitudes: "
            f"total="
            f"{getattr(request_counts, 'total', None)}, "
            f"completadas="
            f"{getattr(request_counts, 'completed', None)}, "
            f"fallidas="
            f"{getattr(request_counts, 'failed', None)}"
        )

    return state


# ============================================================
# 15. DESCARGA
# ============================================================

def download_openai_file(
    client,
    file_id: str,
    destination: Path,
) -> None:

    content = client.files.content(
        file_id
    )

    if hasattr(
        content,
        "write_to_file"
    ):

        content.write_to_file(
            destination
        )

        return

    if hasattr(
        content,
        "read"
    ):

        data = content.read()

    elif hasattr(
        content,
        "content"
    ):

        data = content.content

    else:

        data = bytes(
            content
        )

    if isinstance(
        data,
        str
    ):

        destination.write_text(
            data,
            encoding="utf-8",
        )

    else:

        destination.write_bytes(
            data
        )


# ============================================================
# 16. EXTRACCIÓN DEL OUTPUT
# ============================================================

def extract_output_text(
    response_body: Dict[str, Any]
) -> str:

    output = response_body.get(
        "output",
        [],
    )

    texts: List[str] = []

    for item in output:

        if item.get("type") != "message":
            continue

        for content in item.get(
            "content",
            [],
        ):

            if content.get(
                "type"
            ) == "output_text":

                text = content.get(
                    "text",
                    "",
                )

                if text:
                    texts.append(
                        text
                    )

    return "".join(
        texts
    ).strip()


# ============================================================
# 17. VALIDACIÓN
# ============================================================

def split_evidence(
    value: str
) -> List[str]:

    return [

        item.strip()

        for item in str(
            value
        ).split(";")

        if item.strip()
    ]


def normalize_evidence(
    value: Any
) -> str:

    if value is None:
        return ""

    value = str(
        value
    ).strip()

    if not value:
        return ""

    seen = set()

    result = []

    for item in split_evidence(
        value
    ):

        key = item.casefold()

        if key not in seen:

            seen.add(
                key
            )

            result.append(
                item
            )

    return "; ".join(
        result
    )


def validate_classification(
    result: Dict[str, Any],
    expected_id: str,
) -> Tuple[
    bool,
    List[str],
    Dict[str, Any]
]:

    errors: List[str] = []

    if result.get("id") != expected_id:

        errors.append(
            f"ID devuelto "
            f"({result.get('id')}) "
            f"no coincide con custom_id "
            f"({expected_id})."
        )

    categorias = result.get(
        "categorias"
    )

    if not isinstance(
        categorias,
        dict
    ):

        errors.append(
            "Falta el objeto categorias."
        )

        return (
            False,
            errors,
            result,
        )

    expected_category_names = {

        category

        for (
            category,
            _,
            _
        ) in CATEGORIES
    }

    received_category_names = set(
        categorias.keys()
    )

    missing = (
        expected_category_names
        - received_category_names
    )

    extra = (
        received_category_names
        - expected_category_names
    )

    if missing:

        errors.append(
            f"Categorías faltantes: "
            f"{sorted(missing)}"
        )

    if extra:

        errors.append(
            f"Categorías no permitidas: "
            f"{sorted(extra)}"
        )

    for (
        category,
        _,
        has_entities,
    ) in CATEGORIES:

        data = categorias.get(
            category
        )

        if not isinstance(
            data,
            dict
        ):

            errors.append(
                f"{category}: "
                f"estructura ausente o inválida."
            )

            continue

        presencia = data.get(
            "presencia"
        )

        sem = normalize_evidence(
            data.get(
                "sem",
                "",
            )
        )

        if presencia not in (
            0,
            1,
        ):

            errors.append(
                f"{category}: "
                f"presencia debe ser 0 o 1."
            )

            continue

        data["sem"] = sem

        if has_entities:

            ent = normalize_evidence(
                data.get(
                    "ent",
                    "",
                )
            )

            data["ent"] = ent

        else:

            ent = ""

        if presencia == 0:

            if sem:

                errors.append(
                    f"{category}: "
                    f"presencia=0 pero sem no está vacío."
                )

            if (
                has_entities
                and ent
            ):

                errors.append(
                    f"{category}: "
                    f"presencia=0 pero ent no está vacío."
                )

        if presencia == 1:

            if not sem and not ent:

                errors.append(
                    f"{category}: "
                    f"presencia=1 sin evidencia sem/ent."
                )

    return (
        len(errors) == 0,
        errors,
        result,
    )


# ============================================================
# 18. LAS 76 COLUMNAS
# ============================================================

def statistical_columns() -> List[str]:

    columns = [
        "ID"
    ]

    for (
        category,
        _,
        has_entities,
    ) in CATEGORIES:

        columns.append(
            category
        )

        columns.append(
            f"{category}_sem"
        )

        if has_entities:

            columns.append(
                f"{category}_ent"
            )

    if len(columns) != 76:

        raise AssertionError(
            f"Error interno: "
            f"se generaron {len(columns)} "
            f"columnas, no 76."
        )

    return columns


STATISTICAL_COLUMNS = (
    statistical_columns()
)


def flatten_result(
    result: Dict[str, Any]
) -> Dict[str, Any]:

    row: Dict[str, Any] = {
        "ID":
            result["id"]
    }

    categorias = result[
        "categorias"
    ]

    for (
        category,
        _,
        has_entities,
    ) in CATEGORIES:

        data = categorias[
            category
        ]

        row[
            category
        ] = int(
            data["presencia"]
        )

        row[
            f"{category}_sem"
        ] = normalize_evidence(
            data.get(
                "sem",
                "",
            )
        )

        if has_entities:

            row[
                f"{category}_ent"
            ] = normalize_evidence(
                data.get(
                    "ent",
                    "",
                )
            )

    return row


# ============================================================
# 19. PARSEO DEL RESULTADO BATCH
# ============================================================

def parse_batch_output(
    output_path: Path,
) -> Tuple[
    Dict[str, Dict[str, Any]],
    List[Dict[str, Any]]
]:

    valid_results: Dict[
        str,
        Dict[str, Any]
    ] = {}

    validation_rows: List[
        Dict[str, Any]
    ] = []

    with output_path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        for (
            line_number,
            line,
        ) in enumerate(
            handle,
            start=1,
        ):

            line = line.strip()

            if not line:
                continue

            try:

                batch_item = json.loads(
                    line
                )

            except json.JSONDecodeError as exc:

                validation_rows.append({

                    "ID": "",

                    "estado":
                        "ERROR_JSONL",

                    "detalle":
                        f"Línea {line_number}: "
                        f"{exc}",
                })

                continue

            custom_id = str(
                batch_item.get(
                    "custom_id",
                    "",
                )
            ).strip()

            response_wrapper = (
                batch_item.get(
                    "response"
                )
            )

            if not response_wrapper:

                error = batch_item.get(
                    "error"
                )

                validation_rows.append({

                    "ID":
                        custom_id,

                    "estado":
                        "ERROR_API",

                    "detalle":
                        json.dumps(
                            error,
                            ensure_ascii=False,
                        ),
                })

                continue

            status_code = (
                response_wrapper.get(
                    "status_code"
                )
            )

            if status_code != 200:

                validation_rows.append({

                    "ID":
                        custom_id,

                    "estado":
                        "ERROR_HTTP",

                    "detalle":
                        f"HTTP {status_code}: "
                        + json.dumps(
                            response_wrapper.get(
                                "body"
                            ),
                            ensure_ascii=False,
                        ),
                })

                continue

            body = response_wrapper.get(
                "body",
                {},
            )

            if body.get(
                "status"
            ) == "incomplete":

                validation_rows.append({

                    "ID":
                        custom_id,

                    "estado":
                        "RESPUESTA_INCOMPLETA",

                    "detalle":
                        json.dumps(
                            body.get(
                                "incomplete_details"
                            ),
                            ensure_ascii=False,
                        ),
                })

                continue

            output_text = (
                extract_output_text(
                    body
                )
            )

            if not output_text:

                validation_rows.append({

                    "ID":
                        custom_id,

                    "estado":
                        "SIN_OUTPUT_TEXT",

                    "detalle":
                        "La Response API no devolvió output_text.",
                })

                continue

            try:

                result = json.loads(
                    output_text
                )

            except json.JSONDecodeError as exc:

                validation_rows.append({

                    "ID":
                        custom_id,

                    "estado":
                        "JSON_RESPUESTA_INVALIDO",

                    "detalle":
                        str(exc),
                })

                continue

            (
                is_valid,
                errors,
                normalized_result,
            ) = validate_classification(

                result=result,

                expected_id=
                    custom_id,
            )

            if not is_valid:

                validation_rows.append({

                    "ID":
                        custom_id,

                    "estado":
                        "ERROR_VALIDACION",

                    "detalle":
                        " | ".join(
                            errors
                        ),
                })

                continue

            if custom_id in valid_results:

                validation_rows.append({

                    "ID":
                        custom_id,

                    "estado":
                        "ID_DUPLICADO",

                    "detalle":
                        "El mismo custom_id aparece más de una vez.",
                })

                continue

            valid_results[
                custom_id
            ] = normalized_result

            validation_rows.append({

                "ID":
                    custom_id,

                "estado":
                    "OK",

                "detalle":
                    "",
            })

    return (
        valid_results,
        validation_rows,
    )


# ============================================================
# 20. PRODUCTOS FINALES
# ============================================================

def build_final_outputs(
    valid_results: Dict[str, Dict[str, Any]],
    validation_rows: List[Dict[str, Any]],
) -> None:

    state = load_state()

    run_limit = state.get(
        "limit"
    )

    corpus, _, _ = load_corpus(
        limit=run_limit
    )

    expected_ids = corpus[
        "ID"
    ].tolist()

    result_ids = set(
        valid_results.keys()
    )

    missing_ids = [

        record_id

        for record_id in expected_ids

        if record_id not in result_ids
    ]

    if missing_ids:

        info(
            "ADVERTENCIA: faltan resultados válidos "
            f"para {len(missing_ids)} abstracts."
        )

    statistical_rows: List[
        Dict[str, Any]
    ] = []

    for record_id in expected_ids:

        if record_id not in valid_results:
            continue

        statistical_rows.append(
            flatten_result(
                valid_results[
                    record_id
                ]
            )
        )

    statistical_df = pd.DataFrame(
        statistical_rows,
        columns=
            STATISTICAL_COLUMNS,
    )

    if (
        list(
            statistical_df.columns
        )
        != STATISTICAL_COLUMNS
    ):

        fatal(
            "La estructura de columnas finales "
            "no coincide con la estructura obligatoria."
        )

    if len(
        statistical_df.columns
    ) != 76:

        fatal(
            "La base estadística no tiene "
            "exactamente 76 columnas."
        )

    statistical_df.to_csv(

        STATISTICAL_CSV_PATH,

        index=False,

        encoding="utf-8-sig",
    )

    statistical_df.to_excel(

        STATISTICAL_XLSX_PATH,

        index=False,

        engine="openpyxl",
    )

    abstract_by_id = {

        row["ID"]:
            row["__ABSTRACT__"]

        for _, row in corpus.iterrows()
    }

    annotated_rows: List[
        Dict[str, Any]
    ] = []

    for row in statistical_rows:

        record_id = row[
            "ID"
        ]

        annotated_row: Dict[
            str,
            Any
        ] = {

            "ID":
                record_id,

            "Abstract":
                abstract_by_id[
                    record_id
                ],
        }

        for column in (
            STATISTICAL_COLUMNS[1:]
        ):

            annotated_row[
                column
            ] = row[
                column
            ]

        annotated_rows.append(
            annotated_row
        )

    annotated_columns = (

        [
            "ID",
            "Abstract",
        ]

        + STATISTICAL_COLUMNS[1:]
    )

    annotated_df = pd.DataFrame(

        annotated_rows,

        columns=
            annotated_columns,
    )

    annotated_df.to_csv(

        ANNOTATED_CSV_PATH,

        index=False,

        encoding="utf-8-sig",
    )

    existing_validation_ids = {

        row.get("ID")

        for row in validation_rows
    }

    for record_id in missing_ids:

        if (
            record_id
            not in existing_validation_ids
        ):

            validation_rows.append({

                "ID":
                    record_id,

                "estado":
                    "RESULTADO_FALTANTE",

                "detalle":
                    "No se encontró una respuesta válida para este abstract.",
            })

    validation_df = pd.DataFrame(

        validation_rows,

        columns=[
            "ID",
            "estado",
            "detalle",
        ],
    )

    validation_df.to_csv(

        VALIDATION_REPORT_PATH,

        index=False,

        encoding="utf-8-sig",
    )

    info(
        f"Base estadística: "
        f"{len(statistical_df)} filas × "
        f"{len(statistical_df.columns)} columnas."
    )

    info(
        f"Corpus anotado: "
        f"{len(annotated_df)} filas × "
        f"{len(annotated_df.columns)} columnas."
    )

    info(
        f"Resultados válidos: "
        f"{len(valid_results)} / "
        f"{len(expected_ids)}"
    )

    info(
        f"CSV estadístico: "
        f"{STATISTICAL_CSV_PATH}"
    )

    info(
        f"XLSX estadístico: "
        f"{STATISTICAL_XLSX_PATH}"
    )

    info(
        f"Corpus anotado: "
        f"{ANNOTATED_CSV_PATH}"
    )

    info(
        f"Validación: "
        f"{VALIDATION_REPORT_PATH}"
    )


# ============================================================
# 21. RECOLECCIÓN
# ============================================================

def collect_batch() -> None:

    state = check_status()

    status = state.get(
        "status"
    )

    if status != "completed":

        fatal(
            "El Batch todavía no está completado. "
            f"Estado actual: {status}"
        )

    output_file_id = state.get(
        "output_file_id"
    )

    error_file_id = state.get(
        "error_file_id"
    )

    if not output_file_id:

        fatal(
            "El Batch figura como completed "
            "pero no contiene output_file_id."
        )

    client = get_openai_client()

    info(
        "Descargando resultados del Batch..."
    )

    download_openai_file(

        client,

        output_file_id,

        BATCH_RAW_OUTPUT_PATH,
    )

    info(
        f"Resultado bruto descargado: "
        f"{BATCH_RAW_OUTPUT_PATH}"
    )

    if error_file_id:

        download_openai_file(

            client,

            error_file_id,

            BATCH_RAW_ERROR_PATH,
        )

        info(
            f"Archivo de errores descargado: "
            f"{BATCH_RAW_ERROR_PATH}"
        )

    (
        valid_results,
        validation_rows,
    ) = parse_batch_output(
        BATCH_RAW_OUTPUT_PATH
    )

    build_final_outputs(

        valid_results=
            valid_results,

        validation_rows=
            validation_rows,
    )

    state["status"] = (
        "collected"
    )

    state["valid_results"] = (
        len(valid_results)
    )

    save_state(
        state
    )


# ============================================================
# 22. RESUMEN
# ============================================================

def show_configuration() -> None:

    print()

    print(
        "============================================================"
    )

    print(
        "CONFIGURACIÓN DEL ORQUESTADOR"
    )

    print(
        "============================================================"
    )

    print(
        f"Repositorio:        "
        f"{REPO_ROOT}"
    )

    print(
        f"Corpus:             "
        f"{CORPUS_PATH}"
    )

    print(
        f"Modelo:             "
        f"{MODEL}"
    )

    print(
        f"Reasoning effort:   "
        f"{REASONING_EFFORT}"
    )

    print(
        f"Endpoint Batch:     "
        f"{BATCH_ENDPOINT}"
    )

    print(
        f"SKOS:               "
        f"{len(SKOS_FILES)}"
    )

    print(
        f"Categorías:         "
        f"{len(CATEGORIES)}"
    )

    print(
        f"Columnas finales:   "
        f"{len(STATISTICAL_COLUMNS)}"
    )

    print(
        f"Resultados:         "
        f"{OUTPUT_DIR}"
    )

    print(
        "============================================================"
    )

    print()


# ============================================================
# 23. CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(

        description=(
            "Orquestador para clasificación semántica "
            "y ontológicamente guiada de abstracts."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # PREPARE
    prepare_parser = (
        subparsers.add_parser(

            "prepare",

            help=(
                "Valida corpus y SKOS y crea "
                "batch_input.jsonl. "
                "No realiza llamadas pagas a OpenAI."
            ),
        )
    )

    prepare_parser.add_argument(

        "--limit",

        type=int,

        default=None,

        help=(
            "Número máximo de abstracts "
            "a preparar. "
            "Ejemplo: --limit 40. "
            "Si se omite, procesa todos."
        ),
    )

    # SUBMIT
    subparsers.add_parser(

        "submit",

        help=(
            "Sube batch_input.jsonl "
            "y crea el Batch API."
        ),
    )

    # STATUS
    subparsers.add_parser(

        "status",

        help=(
            "Consulta el estado del Batch."
        ),
    )

    # COLLECT
    subparsers.add_parser(

        "collect",

        help=(
            "Si el Batch terminó, descarga, "
            "valida y genera los productos finales."
        ),
    )

    # CONFIG
    subparsers.add_parser(

        "config",

        help=(
            "Muestra la configuración "
            "sin ejecutar el análisis."
        ),
    )

    return parser


# ============================================================
# 24. MAIN
# ============================================================

def main() -> None:

    show_configuration()

    parser = build_parser()

    args = parser.parse_args()

    if args.command == "prepare":

        prepare_batch(
            limit=args.limit
        )

    elif args.command == "submit":

        submit_batch()

    elif args.command == "status":

        check_status()

    elif args.command == "collect":

        collect_batch()

    elif args.command == "config":

        pass

    else:

        parser.print_help()

        sys.exit(2)


if __name__ == "__main__":
    main()
