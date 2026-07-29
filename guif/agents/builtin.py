from __future__ import annotations

from guif.agents.base import Agent, ContractAgent
from guif.agents.planner import StructuredPlannerAgent


def build_default_agents() -> tuple[Agent, ...]:
    return (
        StructuredPlannerAgent(),
        ContractAgent("director", "Check art direction, reuse opportunities, and production coherence."),
        ContractAgent("theme", "Resolve active theme rules and visual constraints."),
        ContractAgent("resource", "Resolve resource contracts, naming, dimensions, and engine targets."),
        ContractAgent("prompt", "Build model-neutral generation instructions from task context."),
        ContractAgent("qa", "Evaluate outputs against semantic and technical constraints."),
        ContractAgent("export", "Prepare validated outputs for the configured engine adapter."),
    )
