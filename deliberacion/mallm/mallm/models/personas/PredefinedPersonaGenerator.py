from mallm.models.Chat import Chat
from mallm.models.personas.PersonaGenerator import PersonaGenerator
from mallm.utils.types import InputExample


class PredefinedPersonaGenerator(PersonaGenerator):
    """
    Loads predefined personas from sample.metadata["personas"].
    """

    def __init__(self, llm: Chat):
        self.llm = llm

    @classmethod
    def generate_persona(
        cls,
        task_description: str,
        already_generated_personas: list[dict[str, str]],
        sample: InputExample,
    ) -> dict[str, str]:
        if sample.metadata is None or "personas" not in sample.metadata:
            raise ValueError(
                'PredefinedPersonaGenerator requires metadata["personas"].'
            )

        personas = sample.metadata["personas"]
        index = len(already_generated_personas)

        if index >= len(personas):
            raise ValueError("Not enough predefined personas in metadata.")

        persona = personas[index]

        if "role" not in persona or "description" not in persona:
            raise ValueError(
                'Each predefined persona requires "role" and "description".'
            )

        return {
            "role": persona["role"],
            "description": persona["description"],
        }
