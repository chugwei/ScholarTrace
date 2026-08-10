"""Human decision records for auditable research workflows."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

DecisionAction = Literal["approved", "rejected", "modified", "cancelled", "paused"]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DecisionRecord(BaseModel):
    """One human decision bound to a project thread and target entity."""

    model_config = ConfigDict(extra="forbid")

    decision_id: NonBlankText
    project_id: NonBlankText
    thread_id: NonBlankText
    target_type: Literal["research_question"]
    target_id: NonBlankText
    action: DecisionAction
    actor_id: NonBlankText
    reason: NonBlankText | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @model_validator(mode="after")
    def require_reason_for_non_approval(self) -> "DecisionRecord":
        if self.action != "approved" and self.reason is None:
            raise ValueError("reason is required for non-approval decisions")
        return self
