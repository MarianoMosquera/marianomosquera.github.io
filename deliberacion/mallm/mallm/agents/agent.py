from __future__ import annotations

import dataclasses
import logging
import uuid
from typing import TYPE_CHECKING, Optional

import httpx

from mallm.models.Chat import Chat
from mallm.models.discussion.ResponseGenerator import ResponseGenerator

if TYPE_CHECKING:
    from mallm.coordinator import Coordinator

from mallm.utils.types import Agreement, Memory, Response, TemplateFilling

logger = logging.getLogger("mallm")


class Agent:
    """
    Represents an Agent in the discussion, capable of improving, drafting, and providing feedback.
    """

    def __init__(
        self,
        llm: Chat,
        client: httpx.Client,
        coordinator: Coordinator,
        response_generator: ResponseGenerator,
        persona: str,
        persona_description: str,
        chain_of_thought: bool = False,
        drafting_agent: bool = False,
    ):
        """
        Initializes an Agent with the necessary components for facilitating discussions.
        """
        self.id = str(uuid.uuid4())
        self.short_id = self.id[:4]
        self.persona = persona
        self.persona_description = persona_description
        self.coordinator = coordinator
        self.llm = llm
        self.response_generator = response_generator
        self.client = client
        self.chain_of_thought = chain_of_thought
        self.drafting_agent = drafting_agent
        self.memory: dict[str, Memory] = {}
        logger.info(
            f"Creating agent [bold blue]{self.short_id}[/] with personality [bold blue]{self.persona}[/]: {self.persona_description}"
        )

    def improve(
        self,
        unique_id: int,
        turn: int,
        memory_ids: list[int],
        template_filling: TemplateFilling,
        agreements: list[Agreement],
    ) -> tuple[str, Memory, list[Agreement]]:
        """
        Agent improves a solution based on the current state of the discussion.
        """
        logger.debug(f"Agent [bold blue]{self.short_id}[/] is improving the solution.")
        response = self.response_generator.generate_improve(
            template_filling, self.chain_of_thought
        )
        first_draft_response: Response | None = None
        skos_prompt: str | None = None
        second_draft_response: Response | None = None

        if (
            turn == 1
            and template_filling.current_draft is None
            and self.coordinator.skos_processor is not None
        ):
            first_draft_response = response

            skos_prompt = self.coordinator.skos_processor.build_semantic_prompt(
                first_draft=first_draft_response.message,
                persona=self.persona,
                persona_description=self.persona_description,
            )

            second_draft_response = self.response_generator.generate_response(
                [{"role": "user", "content": skos_prompt}],
                template_filling.task_instruction,
                template_filling.input_str,
                self.chain_of_thought,
                None,
                False,
                True,
            )
            response = second_draft_response

        logger.debug(
            f"Agent [bold blue]{self.short_id}[/] {'agreed' if response.agreement else 'disagreed'} with the solution."
        )
        # First-turn SKOS second drafts are independent positions,
        # not agreement/disagreement votes on a collective solution.
        if second_draft_response is not None:
            agree = False
        else:
            agree = False if unique_id == 0 else response.agreement
        agreements.append(
            Agreement(
                agreement=agree,
                response=response.message,
                solution=response.solution if not agree else agreements[-1].solution,
                agent_id=self.id,
                persona=self.persona,
                message_id=unique_id,
            )
        )

        additional_args = dataclasses.asdict(template_filling)
        if first_draft_response is not None and second_draft_response is not None:
            additional_args["skos"] = {
                "first_draft_message": first_draft_response.message,
                "first_draft_solution": first_draft_response.solution,
                "semantic_prompt": skos_prompt,
                "second_draft_message": second_draft_response.message,
                "second_draft_solution": second_draft_response.solution,
            }

        memory = Memory(
            message_id=unique_id,
            turn=turn,
            agent_id=self.id,
            persona=self.persona,
            contribution="improve",
            message=response.message,
            agreement=agreements[-1].agreement,
            solution=response.solution if not agree else agreements[-2].solution,
            memory_ids=memory_ids,
            additional_args=additional_args,
        )
        self.coordinator.memory.append(memory)
        return response.message, memory, agreements

    def draft(
        self,
        unique_id: int,
        turn: int,
        memory_ids: list[int],
        template_filling: TemplateFilling,
        agreements: list[Agreement],
        is_neutral: bool = False,
    ) -> tuple[str, Memory, list[Agreement]]:
        """
        Agent drafts a solution based on the current state of the discussion.
        """
        logger.debug(f"Agent [bold blue]{self.short_id}[/] is drafting a solution.")
        response = self.response_generator.generate_draft(
            template_filling, self.chain_of_thought
        )
        agreements.append(
            Agreement(
                agreement=None,
                response=response.message,
                solution=response.solution,
                agent_id=self.id,
                persona=self.persona,
                message_id=unique_id,
            )
        )

        memory = Memory(
            message_id=unique_id,
            turn=turn,
            agent_id=self.id,
            persona=self.persona,
            contribution="draft",
            message=response.message,
            agreement=None,
            solution=response.solution,
            memory_ids=memory_ids,
            additional_args=dataclasses.asdict(template_filling),
        )
        self.coordinator.memory.append(memory)
        return response.message, memory, agreements

    def feedback(
        self,
        unique_id: int,
        turn: int,
        memory_ids: list[int],
        template_filling: TemplateFilling,
        agreements: list[Agreement],
    ) -> tuple[str, Memory, list[Agreement]]:
        """
        Agent provides feedback to a solution based on the current state of the discussion.
        """
        logger.debug(
            f"Agent [bold blue]{self.short_id}[/] provides feedback to a solution."
        )
        response = self.response_generator.generate_feedback(
            template_filling, self.chain_of_thought
        )
        logger.debug(
            f"Agent [bold blue]{self.short_id}[/] {'agreed' if response.agreement else 'disagreed'} with the solution."
        )
        logger.debug(f"Agent [bold blue]{self.short_id}[/]: {response.message}")
        agreements.append(
            Agreement(
                agreement=response.agreement,
                response=response.message,
                solution="",
                agent_id=self.id,
                persona=self.persona,
                message_id=unique_id,
            )
        )

        memory = Memory(
            message_id=unique_id,
            turn=turn,
            agent_id=self.id,
            persona=self.persona,
            contribution="feedback",
            message=response.message,
            agreement=agreements[-1].agreement,
            solution=None,
            memory_ids=memory_ids,
            additional_args=dataclasses.asdict(template_filling),
        )
        self.coordinator.memory.append(memory)
        return response.message, memory, agreements

    def update_memory(self, memory: Memory) -> None:
        """
        Updates the memory of this agent with another discussion entry.
        """
        self.memory[str(memory.message_id)] = memory

    def get_memories(
        self,
        context_length: Optional[int] = None,
        turn: Optional[int] = None,
        include_this_turn: bool = True,
    ) -> tuple[Optional[list[Memory]], list[int], Optional[str]]:
        """
        Retrieves memory data from the agents memory
        """
        memories: list[Memory]
        memory_ids = []
        current_draft = None

        memories = sorted(
            self.memory.values(), key=lambda x: x.message_id, reverse=False
        )
        context_memory = []
        for memory in memories:
            if turn is not None and not include_this_turn and memory.turn >= turn:
                continue

            context_memory.append(memory)
            memory_ids.append(int(memory.message_id))

            if memory.contribution == "draft" or (
                memory.contribution == "improve" and memory.agreement is False
            ):
                current_draft = memory.solution

        return context_memory, memory_ids, current_draft

    def forget_memories(self, turn: int) -> None:
        keys_to_delete = [key for key, memory in self.memory.items() if memory.turn == turn]
        for key in keys_to_delete:
            del self.memory[key]
        logger.debug(f"Forgot memories {keys_to_delete} from turn {turn} from agent {self.id}")

    def get_own_messages(self, context_length: Optional[int] = None) -> list[str]:
        """
        Retrieves memory from the agents memory bucket as a string
        context_length refers to the amount of turns the agent can use as rationale
        Returns: list of strings
        """
        memories, _, _ = self.get_memories(context_length=context_length)
        if memories:
            own_messages = [
                memory.message for memory in memories if memory.agent_id == self.id
            ]
        else:
            own_messages = []
        return own_messages

    def get_discussion_history(
        self,
        context_length: Optional[int] = None,
        turn: Optional[int] = None,
        include_this_turn: bool = True,
    ) -> tuple[Optional[list[dict[str, str]]], list[int], Optional[str]]:
        """
        Retrieves memory from the agents memory as a string
        context_length refers to the amount of turns the agent can memorize the previous discussion
        """
        memories, memory_ids, current_draft = self.get_memories(
            context_length=context_length,
            turn=turn,
            include_this_turn=include_this_turn,
        )
        if memories:
            discussion_history = []
            for memory in memories:
                if memory.agent_id == self.id:
                    discussion_history.append(
                        {"role": "assistant", "content": memory.message}
                    )
                else:
                    discussion_history.append(
                        {
                            "role": "user",
                            "content": f"{memory.persona}: {memory.message}",
                        }
                    )
        else:
            discussion_history = None
        return discussion_history, memory_ids, current_draft
