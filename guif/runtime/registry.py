from __future__ import annotations

from guif.agents.base import Agent


class AgentRegistry:
    def __init__(self, agents: tuple[Agent, ...] = ()) -> None:
        self._agents: dict[str, Agent] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: Agent) -> None:
        if not agent.name:
            raise ValueError("Agent name must not be empty")
        if agent.name in self._agents:
            raise ValueError(f"Agent already registered: {agent.name}")
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(f"Unknown agent: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(self._agents)
