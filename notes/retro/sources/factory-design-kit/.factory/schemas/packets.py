"""Packet contracts for the design-review loop.

One source of truth: agents get JSON Schemas generated from these models
(`python .factory/bin/factory.py schemas`), and the workflow's shell steps
validate every agent-written file against them. The workflow engine only
ever branches on fields of LoopState, which is produced by code.
"""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Stage = Literal["spec", "plan"]
Severity = Literal["blocker", "major", "minor"]


class Finding(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+-\d+$",
                    description="Stable across rounds: '<role>-<n>'. Reuse the id if the issue persists.")
    severity: Severity
    confidence: int = Field(ge=0, le=100, description="How sure you are this is a real problem.")
    artifact: str = Field(max_length=200, description="Path of the file the finding is about.")
    section: str = Field(max_length=120, description="Heading or requirement id within that file.")
    issue: str = Field(max_length=400)
    recommendation: str = Field(max_length=400)


class ReviewVerdict(BaseModel):
    """Written by each reviewer to reviews/<stage>/round-<n>/<role>.json."""
    role: str
    stage: Stage
    round: int = Field(ge=1)
    verdict: Literal["approve", "revise"]
    findings: list[Finding] = Field(default_factory=list,
                                    description="All findings still open after this round. No count cap.")
    resolved: list[str] = Field(default_factory=list,
                                description="Ids from the previous round you now consider resolved.")
    summary: str = Field(max_length=300)

    @model_validator(mode="after")
    def _consistent(self):
        prefix = f"{self.role}-"
        bad = [f.id for f in self.findings if not f.id.startswith(prefix)]
        if bad:
            raise ValueError(f"finding ids must start with '{prefix}': {bad}")
        if self.verdict == "approve" and any(f.severity == "blocker" for f in self.findings):
            raise ValueError("an 'approve' verdict cannot carry blocker findings")
        return self


class Disposition(BaseModel):
    finding_id: str
    action: Literal["fixed", "rejected", "needs_human"]
    rationale: str = Field(max_length=400,
                           description="What changed, why the finding is wrong, or what decision you need.")


class RevisionReport(BaseModel):
    """Written by the reviser to reviews/<stage>/round-<n>/revision.json."""
    stage: Stage
    round: int = Field(ge=1)
    dispositions: list[Disposition]
    changed_files: list[str]


class LoopState(BaseModel):
    """Printed by factory.py; the only thing the workflow branches on."""
    stage: Stage
    round: int
    roles: list[dict] = Field(default_factory=list)
    all_valid: bool = True
    invalid_files: list[str] = Field(default_factory=list)
    open_blocking: int = 0
    converged: bool = False
    continue_loop: bool = False
    needs_escalation: bool = False
