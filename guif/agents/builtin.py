from __future__ import annotations

from guif.agents.base import Agent, ContractAgent
from guif.agents.director import StructuredDirectorAgent
from guif.agents.planner import StructuredPlannerAgent
from guif.agents.resource import StructuredResourceAgent
from guif.agents.theme import StructuredThemeAgent


def build_default_agents() -> tuple[Agent, ...]:
    return (
        StructuredPlannerAgent(),
        StructuredDirectorAgent(),
        StructuredThemeAgent(),
        StructuredResourceAgent(),
        ContractAgent("prompt", "Build model-neutral generation instructions from task context."),
        ContractAgent("qa", "Evaluate outputs against semantic and technical constraints."),
        ContractAgent("export", "Prepare validated outputs for the configured engine adapter."),
    )
