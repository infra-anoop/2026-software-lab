from typing import List, Literal, TypedDict, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    quote: str = Field(description="Verbatim quote from the source text.")
    location: Optional[str] = Field(default=None, description="Optional pointer like page/section/line if available.")


class Claim(BaseModel):
    claim_id: str = Field(description="Stable ID like C1, C2, ...")
    claim: str = Field(description="Short, testable statement derived ONLY from evidence.")
    evidence: List[Evidence] = Field(min_length=1, description="One or more quotes that directly support the claim.")
    notes: Optional[str] = Field(default=None, description="Limits/assumptions, if any.")


class ResearchOutput(BaseModel):
    source_material_title: str = Field(description="Title of the document analyzed.")
    executive_summary: List[str] = Field(min_length=3, description="3–6 bullets summarizing the strongest supported claims.")
    claims: List[Claim] = Field(min_length=3, description="Atomic claims with direct evidence per claim.")
    open_questions: List[str] = Field(default_factory=list, description="Things not supported by quotes yet.")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="How well the text supports these findings.")

    @property
    def key_findings(self) -> List[str]:
        """Compatibility: executive_summary as list of findings for save_to_supabase."""
        return self.executive_summary


class Issue(BaseModel):
    issue_id: str = Field(description="Stable ID like I1, I2, ...")
    severity: Literal["MUST_FIX", "SHOULD_FIX", "NIT"] = Field(description="Controls verdict.")
    category: Literal[
        "UNSUPPORTED_CLAIM",
        "WEAK_SUPPORT",
        "OVER_INFERENCE",
        "MISSING_CONTEXT",
        "CONTRADICTION",
        "UNCLEAR_WORDING",
    ] = Field(description="Type of defect.")
    claim_id: Optional[str] = Field(default=None, description="Which claim this refers to, if applicable.")
    evidence: Optional[str] = Field(default=None, description="Quote or excerpt showing the problem (from research or source).")
    fix_guidance: str = Field(description="Actionable instruction to resolve this issue.")


class AuditFeedback(BaseModel):
    verdict: Literal["PASS", "NEEDS_REVISION", "FAIL"]
    supported_claim_ratio: float = Field(ge=0.0, le=1.0, description="Supported claims / total claims.")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Computed score derived from ratio and penalties.")
    issues: List[Issue] = Field(default_factory=list)
    summary: str = Field(description="1–3 sentences: why this verdict.")
    next_action: str = Field(description="If NEEDS_REVISION, what to do next in one paragraph.")

    @property
    def critique_points(self) -> List[str]:
        """Compatibility: issues as list of critique strings for save_to_supabase."""
        return [f"{i.issue_id} ({i.severity}): {i.fix_guidance}" for i in self.issues]


class FinalState(TypedDict):
    """Workflow output passed to save_to_supabase: research, feedback, iterations."""

    research: ResearchOutput
    feedback: AuditFeedback
    iterations: int
