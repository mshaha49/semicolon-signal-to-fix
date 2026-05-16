"""
OrchestrationService
====================

Entry point for inbound workflow session events. Enriches the event with
metadata, hands off to WorkflowAssignmentService, and translates any
uncaught failures into a ServiceException with a logged stack trace.
"""
import logging
import traceback
from typing import Any, Dict

logger = logging.getLogger("workflow.orchestration")


class ServiceException(Exception):
    """Wraps any unhandled assignment failure surfaced from downstream."""


class SessionContext:
    """Per-request context passed into the assignment pipeline."""

    def __init__(
        self,
        request_id: str,
        session_id: str,
        skill_group: str,
        metadata: Dict[str, Any] = None,
    ):
        self.request_id = request_id
        self.session_id = session_id
        self.skill_group = skill_group
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return (
            f"SessionContext(requestId={self.request_id}, "
            f"sessionId={self.session_id}, skillGroup={self.skill_group})"
        )


class OrchestrationService:
    def __init__(self, assignment_service):
        self.assignment_service = assignment_service

    def enrich_metadata(self, event: Dict[str, Any]) -> SessionContext:
        """Construct a SessionContext from a raw event payload."""
        return SessionContext(
            request_id=event.get("request_id"),
            session_id=event.get("session_id"),
            skill_group=event.get("skill_group", "tier1"),
            metadata={
                "tenant": event.get("tenant", "default"),
                "received_at": event.get("ts"),
            },
        )

    def handle_session_event(self, event: Dict[str, Any]):
        ctx = self.enrich_metadata(event)
        logger.info(
            "handleSessionEvent received requestId=%s sessionId=%s",
            ctx.request_id, ctx.session_id,
        )

        try:
            result = self.assignment_service.assign_agent(ctx)
            logger.info(
                "session assigned requestId=%s sessionId=%s agentId=%s",
                ctx.request_id, ctx.session_id, getattr(result.agent, "id", "?"),
            )
            return result
        except Exception as e:
            logger.error(
                "Unhandled exception in handleSessionEvent requestId=%s sessionId=%s",
                ctx.request_id, ctx.session_id,
            )
            logger.error(traceback.format_exc())
            raise ServiceException(
                f"session {ctx.session_id} failed: {e}"
            ) from e
