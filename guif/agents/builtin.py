from __future__ import annotations

from guif.agents.base import Agent, ContractAgent
from guif.agents.director import StructuredDirectorAgent
from guif.agents.planner import StructuredPlannerAgent
from guif.agents.prompt import StructuredPromptAgent
from guif.agents.qa import StructuredSemanticQAAgent
from guif.agents.resource import StructuredResourceAgent
from guif.agents.theme import StructuredThemeAgent


def build_default_agents() -> tuple[Agent, ...]:
    return (
        StructuredPlannerAgent(),
        StructuredDirectorAgent(),
        StructuredThemeAgent(),
        StructuredResourceAgent(),
        StructuredPromptAgent(),
        StructuredSemanticQAAgent(),
        ContractAgent("export", "Prepare validated outputs for the configured engine adapter."),
    )
