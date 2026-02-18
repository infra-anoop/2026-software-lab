from typing import List, Literal, TypedDict

from pydantic import BaseModel, Field


class ResearchOutput(BaseModel):
    """The structured data produced by the Researcher Agent."""
    source_material_title: str = Field(
        description="The title of the document analyzed."
    )
    key_findings: List[str] = Field(
        min_length=3,
        description="At least 3 specific technical findings extracted from the text."
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="0.0 to 1.0 score of how well the text supports these findings."
    )
    supporting_quotes: List[str] = Field(
        description="Direct snippets from the text for verification."
    )


class AuditFeedback(BaseModel):
    """The structured critique produced by the Critic Agent."""
    verdict: Literal["PASS", "FAIL", "NEEDS_REVISION"] = Field(
        description="The final status. PASS: logic is sound. FAIL: source is invalid. NEEDS_REVISION: fixable issues."
    )
    critique_points: List[str] = Field(
        default_factory=list,
        description="Specific technical reasons for the verdict."
    )
    suggested_focus: str = Field(
        description="Actionable guidance for the researcher if revision is needed."
    )


class FinalState(TypedDict):
    """Workflow output passed to save_to_supabase: research, feedback, iterations."""

    research: ResearchOutput
    feedback: AuditFeedback
    iterations: int
