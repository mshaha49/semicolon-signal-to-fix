"""
WorkflowAssignmentService
=========================

Matches incoming workflow sessions to an available agent. Queries PoolService
for eligible agents within the requested skill group, ranks them, and returns
the top-ranked agent wrapped in an AssignmentResult.

Behavior:
- When the pool has eligible agents, the top-ranked one is assigned.
- When `assignment.fallback.enabled=true` and the pool is empty, a fallback
  strategy is engaged.
- When `assignment.fallback.enabled=false`, no fallback is triggered.

NOTE: there is a bug in `assign_agent` — the empty-pool path is not guarded
before indexing into the ranked list. See line ~52.
"""
import logging
from typing import Any, List, Optional

logger = logging.getLogger("workflow.assignment")


class AssignmentResult:
    """Result wrapper returned by the assignment service."""

    def __init__(self, agent: Any):
        self.agent = agent

    def __repr__(self) -> str:
        return f"AssignmentResult(agent_id={getattr(self.agent, 'id', '?')})"


class WorkflowAssignmentService:
    def __init__(self, pool_service, ranker, config):
        self.pool_service = pool_service
        self.ranker = ranker
        self.config = config

    def is_fallback_enabled(self) -> bool:
        return self.config.get_bool("assignment.fallback.enabled", default=False)

    def assign_agent(self, ctx) -> AssignmentResult:
        request_id = ctx.request_id
        session_id = ctx.session_id
        skill_group = ctx.skill_group

        logger.info(
            "assignAgent start requestId=%s sessionId=%s skillGroup=%s",
            request_id, session_id, skill_group,
        )

        pool = self.pool_service.get_eligible_agents(skill_group, ctx)
        ranked_pool = self.ranker.rank(pool)

        # BUG: no empty/null guard on ranked_pool — raises IndexError when the
        # pool is empty. The fallback block below is therefore never reached.
        result = ranked_pool[0]

        if result is None and self.is_fallback_enabled():
            logger.warning(
                "primary assignment empty, attempting fallback requestId=%s",
                request_id,
            )
            return self._fallback(ctx)

        logger.info(
            "assignAgent ok requestId=%s sessionId=%s agentId=%s",
            request_id, session_id, getattr(result, "id", "?"),
        )
        return AssignmentResult(result)

    def _fallback(self, ctx) -> AssignmentResult:
        """Fallback strategy. Currently unreachable due to the bug above."""
        logger.error(
            "fallback engaged requestId=%s skillGroup=%s",
            ctx.request_id, ctx.skill_group,
        )
        raise NotImplementedError("fallback strategy not implemented yet")
