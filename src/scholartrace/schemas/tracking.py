"""Optional experiment tracking and DVC provenance contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scholartrace.schemas.research import NonBlankText

TrackingStatus = Literal["recorded", "unavailable", "failed"]
DataVersionStatus = Literal["verified", "mismatch", "unavailable"]


class TrackingAttempt(BaseModel):
    """Result of an optional tracker call, including explicit degradation."""

    model_config = ConfigDict(extra="forbid")

    execution_id: NonBlankText
    provider: NonBlankText
    status: TrackingStatus
    reason: NonBlankText | None = None
    record_path: NonBlankText | None = None
    recorded_at: datetime


class DVCDataVersionCheck(BaseModel):
    """Hash comparison between a local file and a DVC-style manifest."""

    model_config = ConfigDict(extra="forbid")

    path: NonBlankText
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    actual_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    status: DataVersionStatus
    source: Literal["dvc_manifest", "unavailable"]
    reason: NonBlankText | None = None
    checked_at: datetime
