"""
PoolService
===========

Maintains the set of available agents per skill group. Returns an empty list
silently when a skill group has not been initialized or its pool is exhausted —
callers are expected to check for empty results.
"""
import logging
from typing import List

logger = logging.getLogger("workflow.pool")


class Agent:
    def __init__(self, id: str, skill_group: str, available: bool = True):
        self.id = id
        self.skill_group = skill_group
        self.available = available


class PoolService:
    def __init__(self):
        self._pools = {}  # skill_group -> list[Agent]

    def initialize(self, skill_group: str, agents: List[Agent]) -> None:
        """Seed (or reseed) the pool for a skill group with available agents."""
        self._pools[skill_group] = [a for a in agents if a.available]
        logger.info(
            "pool initialized skillGroup=%s available=%d",
            skill_group, len(self._pools[skill_group]),
        )

    def get_eligible_agents(self, skill_group: str, ctx) -> List[Agent]:
        """Return the live list of agents for the given skill group.

        Returns empty list - no exception raised. Callers MUST guard against
        an empty result before indexing.
        """
        agents = self._pools.get(skill_group, [])
        logger.debug(
            "pool query skillGroup=%s requestId=%s available=%d",
            skill_group, getattr(ctx, "request_id", "?"), len(agents),
        )
        return agents
