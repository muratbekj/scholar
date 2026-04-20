from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SupportLevel(str, Enum):
    GROUNDED = "grounded"
    INFERRED = "inferred"
    WEAK_SUPPORT = "weak_support"


class ReflectionState(str, Enum):
    REQUIRED = "required"
    SUBMITTED = "submitted"
    BYPASSED = "bypassed"


class QAResponseState(str, Enum):
    PENDING_REFLECTION = "pending_reflection"
    ANSWERED = "answered"


class QuizMode(str, Enum):
    STANDARD = "standard"
    REASONING_GAP = "reasoning_gap"
    AI_OVERSIGHT = "ai_oversight"


class QAGenerationMode(str, Enum):
    STANDARD = "standard"
    REASONING_GAP = "reasoning_gap"


class EvidenceRef(BaseModel):
    chunk_id: Optional[str] = None
    excerpt: Optional[str] = None
    source_file: Optional[str] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    page_number: Optional[int] = None
    score: Optional[float] = None
    label: Optional[str] = None
    support_tier: Optional[str] = None
    score_band: Optional[str] = None


class GapStep(BaseModel):
    order: int
    prompt: str
    placeholder: str
    expected_concept: Optional[str] = None
    rubric_hint: Optional[str] = None
    learner_response: Optional[str] = None
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)


class SourceLink(BaseModel):
    """Verification anchor for grounded text — use for PDF / chunk navigation in the client."""

    excerpt: str = Field(default="", max_length=600)
    page_number: Optional[int] = None
    chunk_id: Optional[str] = None
    source_file: Optional[str] = None
    segment_index: Optional[int] = None
    support_level: str = "grounded"


class AnswerSegment(BaseModel):
    """One span of the assistant answer with audit / heatmap metadata.

    `source_match_percent` is a coarse 0–100 composite (tier + best retrieval score);
    it is heuristic, not a calibrated probability—use for UI bands, not guarantees.
    """

    text: str
    support_level: SupportLevel
    support_tier: Optional[str] = None
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    # Human-readable tier for tooltips / legend (Value-Sensitive Design copy)
    support_label_ui: Optional[str] = None
    # Composite “how well does this track the cited evidence” (see API.md)
    source_match_percent: Optional[int] = None


class AuditSummary(BaseModel):
    summary: str
    grounded_segments: int = 0
    inferred_segments: int = 0
    weak_support_segments: int = 0
    recent_history_summary: Optional[str] = None
    # Grounded spans linked to evidence for verification (anti–black-box / Cristianini shortcut visibility)
    source_links: List[SourceLink] = Field(default_factory=list)
