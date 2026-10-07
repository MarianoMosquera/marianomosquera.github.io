from pathlib import Path

from rdflib import Graph


class SKOSProcessor:
    """
    Carga las ontologías SKOS utilizadas como marco semántico
    para interpretar la posición inicial de cada agente.

    La ontología no se utiliza como diccionario ni como sistema
    de coincidencia de palabras. Sus conceptos, jerarquías y
    relaciones constituyen un marco semántico general y prioritario
    para la interpretación del primer draft.
    """

    ONTOLOGY_FILES = [
        "racionalidad.ttl",
        "valores.ttl",
        "social.ttl",
        "politica.ttl",
        "institucional.ttl",
        "tecnologica.ttl",
        "ambiental.ttl",
        "economica.ttl",
        "accountability.ttl",
        "engagement.ttl",
        "compliance.ttl",
    ]

    def __init__(self, ontology_dir: str | Path):
        self.ontology_dir = Path(ontology_dir)
        self.graph = Graph()
        self._load_ontologies()

    def _load_ontologies(self) -> None:
        """
        Integra los 11 archivos TTL en un único grafo RDF.
        """
        for filename in self.ONTOLOGY_FILES:
            path = self.ontology_dir / filename

            if not path.exists():
                raise FileNotFoundError(
                    f"No se encontró la ontología SKOS: {path}"
                )

            self.graph.parse(path, format="turtle")
    def build_semantic_prompt(
        self,
        first_draft: str,
        persona: str,
        persona_description: str,
    ) -> str:
        """
        Construye el prompt para reinterpretar el primer draft
        mediante el marco semántico SKOS.
        """

        skos_context = self.graph.serialize(format="turtle")

        return f"""
Eres el mismo agente que produjo la posición inicial incluida más abajo.

PERFIL DEL AGENTE
Rol: {persona}
Descripción: {persona_description}

PRIMER DRAFT
{first_draft}

MARCO SEMÁNTICO SKOS
{skos_context}

INSTRUCCIÓN

Reinterpreta tu primer draft utilizando el marco SKOS anterior como
marco semántico general y prioritario de interpretación.

Las dimensiones, conceptos, jerarquías y relaciones expresadas en SKOS
deben orientar sustantivamente la interpretación de la posición.

No utilices SKOS como un diccionario, una lista de palabras clave,
un mecanismo de coincidencia terminológica ni una taxonomía destinada
simplemente a clasificar el texto.

Interpreta las relaciones semánticas entre conceptos, incluyendo las
relaciones jerárquicas y asociativas, y considera conjuntamente las
dimensiones representadas en las once ontologías.

El marco SKOS tiene prioridad como estructura conceptual de interpretación,
pero no debe sustituir la identidad, experiencia, intereses, conocimientos
ni perspectiva del agente.

No introduzcas retrospectivamente información sobre acontecimientos
posteriores al contexto temporal proporcionado al agente.

A partir de esta reinterpretación, produce una nueva posición argumentativa
del mismo agente. Esta nueva posición constituye el SEGUNDO DRAFT que será
utilizado como posición de entrada a la deliberación.

No describas el procedimiento realizado ni enumeres conceptos SKOS por el
solo hecho de estar presentes en la ontología. Devuelve únicamente la nueva
posición argumentativa del agente.
""".strip()
    def generate_second_draft(
        self,
        llm,
        first_draft: str,
        persona: str,
        persona_description: str,
        semantic_prompt: str | None = None,
    ) -> str:
        """
        Genera el segundo draft del mismo agente utilizando SKOS
        como marco semántico general y prioritario.
        """

        if semantic_prompt is None:
            semantic_prompt = self.build_semantic_prompt(
                first_draft=first_draft,
                persona=persona,
                persona_description=persona_description,
            )

        second_draft = llm.invoke(
            [
                {
                    "role": "user",
                    "content": semantic_prompt,
                }
            ]
        )

        return str(second_draft)
