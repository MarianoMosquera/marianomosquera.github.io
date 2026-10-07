from __future__ import annotations

import dataclasses
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rich.panel import Panel
from rich.progress import Console
from rich.text import Text

from mallm.agents.draftProposer import DraftProposer
from mallm.agents.panelist import Panelist
from mallm.utils.types import Agreement, Memory, TemplateFilling, VotingResultList

if TYPE_CHECKING:
    from mallm.coordinator import Coordinator
    from mallm.utils.config import Config
logger = logging.getLogger("mallm")


class DiscussionParadigm(ABC):
    def __init__(self, paradigm_str: str = "") -> None:
        self.paradigm_str = paradigm_str
        self.decision = False
        self.turn = 0
        self.unique_id = 0
        self.memories: list[Memory] = []
        self.draft = ""
        self.agreements: list[Agreement] = []

    def _save_round1_checkpoint(
        self,
        checkpoint_path: str,
        coordinator: Coordinator,
    ) -> None:
        path = Path(checkpoint_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        agent_order = [
            {
                "index": i,
                "persona": agent.persona,
            }
            for i, agent in enumerate(coordinator.agents)
            if isinstance(agent, Panelist)
        ]

        data = {
            "version": 1,
            "turn": self.turn,
            "unique_id": self.unique_id,
            "agent_order": agent_order,
            "globalMemory": [
                dataclasses.asdict(memory) for memory in coordinator.memory
            ],
            "agreements": [
                dataclasses.asdict(agreement) for agreement in self.agreements
            ],
        }

        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)

    def _load_round1_checkpoint(
        self,
        checkpoint_path: str,
        coordinator: Coordinator,
    ) -> int:
        path = Path(checkpoint_path)
        if not path.exists():
            return 0

        data = json.loads(path.read_text(encoding="utf-8"))
        saved_order = data.get("agent_order", [])
        current_panelists = [
            agent for agent in coordinator.agents if isinstance(agent, Panelist)
        ]

        if len(saved_order) != len(current_panelists):
            raise ValueError(
                "Round 1 checkpoint does not match the current number of panelists."
            )

        old_to_new_agent_id: dict[str, str] = {}
        for saved, current in zip(saved_order, current_panelists):
            if saved["persona"] != current.persona:
                raise ValueError(
                    "Round 1 checkpoint persona order does not match current agents."
                )

        restored_memories: list[Memory] = []
        for raw_memory in data.get("globalMemory", []):
            raw_memory = dict(raw_memory)
            old_id = raw_memory["agent_id"]

            matching_index = next(
                (
                    saved["index"]
                    for saved in saved_order
                    if saved["persona"] == raw_memory["persona"]
                ),
                None,
            )
            if matching_index is None:
                raise ValueError(
                    f'Cannot restore memory for persona: {raw_memory["persona"]}'
                )

            new_id = coordinator.agents[matching_index].id
            old_to_new_agent_id[old_id] = new_id
            raw_memory["agent_id"] = new_id
            restored_memories.append(Memory(**raw_memory))

        restored_agreements: list[Agreement] = []
        for raw_agreement in data.get("agreements", []):
            raw_agreement = dict(raw_agreement)
            old_id = raw_agreement["agent_id"]
            if old_id not in old_to_new_agent_id:
                matching_index = next(
                    (
                        saved["index"]
                        for saved in saved_order
                        if saved["persona"] == raw_agreement["persona"]
                    ),
                    None,
                )
                if matching_index is None:
                    raise ValueError(
                        f'Cannot restore agreement for persona: {raw_agreement["persona"]}'
                    )
                old_to_new_agent_id[old_id] = coordinator.agents[matching_index].id

            raw_agreement["agent_id"] = old_to_new_agent_id[old_id]
            restored_agreements.append(Agreement(**raw_agreement))

        coordinator.memory = restored_memories
        for agent in coordinator.agents:
            agent.memory = {}
        coordinator.update_memories(restored_memories, coordinator.agents)

        self.agreements = restored_agreements
        self.unique_id = int(data.get("unique_id", len(restored_memories)))

        return len(restored_memories)

    def discuss(
        self,
        coordinator: Coordinator,
        task_instruction: str,
        input_str: str,
        solution: str,
        config: Config,
        console: Optional[Console] = None,
    ) -> tuple[
        Optional[str], int, list[Agreement], bool, dict[int, Optional[VotingResultList]]
    ]:
        logger.info(self.paradigm_str)
        voting_process_string = ""
        voting_results_per_turn: dict[int, Optional[VotingResultList]] = {}

        if console is None:
            console = Console()

        round1_completed_agents = 0
        if config.round1_checkpoint_path:
            round1_completed_agents = self._load_round1_checkpoint(
                config.round1_checkpoint_path,
                coordinator,
            )
            if round1_completed_agents:
                if round1_completed_agents == len(coordinator.panelists):
                    self.turn = 1
                else:
                    self.turn = 0

        while (
            not self.decision or config.skip_decision_making
        ) and self.turn < config.max_turns:
            self.turn += 1
            logger.debug(f"Ongoing. Current turn: {self.turn}")

            for i, agent in enumerate(coordinator.agents):
                if (
                    self.turn == 1
                    and config.round1_checkpoint_path
                    and i < round1_completed_agents
                ):
                    continue

                discussion_history, memory_ids, current_draft = (
                    agent.get_discussion_history(
                        context_length=config.visible_turns_in_memory,
                        turn=self.turn,
                        include_this_turn=False,
                    )
                )
                if (
                    self.turn == 1 and config.all_agents_generate_first_draft
                ) or config.all_agents_generate_draft:
                    current_draft = None
                    discussion_history = None
                elif config.decision_protocol == "approval_voting" and self.turn >= 2:
                    # Keep deliberation informationally symmetric across rounds
                    # without privileging any agent as Current Solution.
                    current_draft = None

                template_filling = TemplateFilling(
                    task_instruction=task_instruction,
                    input_str=input_str,
                    current_draft=current_draft,
                    persona=agent.persona,
                    persona_description=agent.persona_description,
                    agent_memory=discussion_history,
                )

                if isinstance(agent, DraftProposer):
                    template_filling.feedback_sentences = None
                    self.draft_proposer_call(
                        draft_proposer=agent,
                        coordinator=coordinator,
                        agent_index=i,
                        memory_ids=memory_ids,
                        template_filling=template_filling,
                    )
                elif isinstance(agent, Panelist):
                    self.panelist_call(
                        agent=agent,
                        coordinator=coordinator,
                        agent_index=i,
                        memory_ids=memory_ids,
                        template_filling=template_filling,
                    )
                elif agent.__class__.__name__ == "Judge":
                    continue    # executes after decision protocol
                else:
                    logger.error("Agent type not recognized.")
                    raise Exception("Agent type not recognized.")
                self.unique_id += 1
                self.memories = []

                if (
                    self.turn == 1
                    and config.round1_checkpoint_path
                    and config.round1_agents_per_run
                ):
                    self._save_round1_checkpoint(
                        config.round1_checkpoint_path,
                        coordinator,
                    )
                    round1_completed_agents += 1

                    if (
                        round1_completed_agents % config.round1_agents_per_run == 0
                    ):
                        logger.info(
                            "Round 1 checkpoint saved after agent "
                            f"{round1_completed_agents}/{len(coordinator.panelists)}."
                        )
                        return (
                            self.draft,
                            self.turn,
                            self.agreements,
                            False,
                            voting_results_per_turn,
                        )


            if coordinator.decision_protocol is None:
                logger.error("No decision protocol module found.")
                raise Exception("No decision protocol module found.")

            # Evaluate consensus only after all agents have completed the round.
            if self.turn == 1 and config.all_agents_generate_first_draft:
                voting_results_per_turn[self.turn] = None
            else:
                (
                    self.draft,
                    self.decision,
                    self.agreements,
                    voting_process_string,
                    additional_voting_results,
                ) = coordinator.decision_protocol.make_decision(
                    self.agreements,
                    self.turn,
                    len(coordinator.agents) - 1,
                    task_instruction,
                    input_str,
                    config,
                )
                if additional_voting_results:
                    voting_results_per_turn[self.turn] = additional_voting_results
                else:
                    voting_results_per_turn[self.turn] = None

            if coordinator.judge and not (
                self.turn == 1 and config.all_agents_generate_first_draft
            ):
                template_filling = TemplateFilling(
                    task_instruction=task_instruction,
                    input_str=input_str,
                    current_draft=self.draft,
                    persona=coordinator.judge.persona,
                    persona_description=coordinator.judge.persona_description,
                    agent_memory=discussion_history,
                )
                self.unique_id, self.turn = coordinator.judge.intervention(self.unique_id, self.turn, memory_ids, template_filling, self.draft, always_intervene=config.judge_always_intervene)

            self.print_messages(coordinator, input_str, task_instruction)

        self.print_messages(
            coordinator,
            input_str,
            task_instruction,
            False,
            solution,
            voting_process_string,
            console,
        )
        return (
            self.draft,
            self.turn,
            self.agreements,
            self.decision,
            voting_results_per_turn,
        )

    def print_messages(
        self,
        coordinator: Coordinator,
        input_str: str,
        task_instruction: str,
        only_current_turn: bool = True,
        solution: str = "",
        voting_process_string: str = "",
        console: Optional[Console] = None,
    ) -> None:
        if console is None:
            console = Console()
        global_memories = [
            memory
            for memory in coordinator.memory
            if memory.turn == self.turn or not only_current_turn
        ]
        if not global_memories:  # if the regenerate judge intervention is triggered, the memory is empty
            return

        max_width = min(console.width, 100)
        discussion_text = Text(
            f"Task instruction: {task_instruction}\n\nInput: {input_str}\n-----------\n"
            + "\n-----------\n".join(
                [
                    f"Agent ({m.persona})({'agreed' if m.agreement else 'disagreed'}): {m.message}"
                    for m in global_memories
                ]
            )
            + f"\n-----------\nDecision Success: {self.decision} \n\nReal Solution: {solution}\nDiscussion solution: {self.draft}"
            + (f"\n\n{voting_process_string}" if voting_process_string else "")
        )
        discussion_text.highlight_regex(r"Agent .*\):", style="bold green")
        discussion_text.highlight_regex(r"Task instruction:", style="bold green")
        discussion_text.highlight_regex(r"Input:", style="bold green")
        discussion_text.highlight_regex(r"Decision Success:", style="bold green")
        discussion_text.highlight_regex(r"Accepted solution:", style="bold green")
        discussion_text.highlight_regex(r"Voting with alteration:", style="bold green")
        discussion_text.highlight_regex(r".* final answer:", style="bold green")
        discussion_text.highlight_regex(r"Facts:", style="bold green")
        discussion_text.highlight_regex(r"####.*", style="bold green")
        for panelist in coordinator.panelists:
            discussion_text.highlight_regex(panelist.persona, style="bold blue")
        panel = Panel(
            discussion_text,
            title=(
                f"Discussion Turn {global_memories[0].turn}"
                if only_current_turn
                else "Discussion"
            ),
            subtitle=f"Decision: {self.decision}",
            expand=False,
            width=max_width,
        )
        console.print(panel)

    @abstractmethod
    def draft_proposer_call(
        self,
        draft_proposer: DraftProposer,
        coordinator: Coordinator,
        agent_index: int,
        memory_ids: list[int],
        template_filling: TemplateFilling,
    ) -> None:
        pass

    @abstractmethod
    def panelist_call(
        self,
        agent: Panelist,
        coordinator: Coordinator,
        agent_index: int,
        memory_ids: list[int],
        template_filling: TemplateFilling,
    ) -> None:
        pass
