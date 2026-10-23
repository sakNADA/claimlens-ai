from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    review = "review"
    approved = "approved"
    rejected = "rejected"


class ClaimCreate(BaseModel):
    claimant: str = Field(min_length=2, max_length=100)
    policy_number: str = Field(pattern=r"^POL-[A-Z0-9-]{4,20}$")
    incident_description: str = Field(min_length=12, max_length=2000)
    damage_description: str = Field(default="", max_length=2000)
    claimed_amount: float = Field(gt=0, le=1_000_000)
    invoice_text: str = Field(default="", max_length=5000)


class RiskFactor(BaseModel):
    code: str
    label: str
    points: int
    evidence: str


class Claim(BaseModel):
    id: str
    claimant: str
    policy_number: str
    incident_description: str
    damage_description: str
    claimed_amount: float
    extracted_invoice_amount: float | None
    risk_score: int
    risk_level: Literal["low", "medium", "high"]
    status: ClaimStatus
    risk_factors: list[RiskFactor]
    created_at: str


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected", "review"]
    reviewer: str = Field(min_length=2, max_length=80)
    note: str = Field(min_length=3, max_length=500)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=4, max_length=500)


class Citation(BaseModel):
    clause_id: str
    title: str
    excerpt: str
    relevance: float


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool


class AuditEvent(BaseModel):
    id: int
    claim_id: str
    event_type: str
    actor: str
    detail: str
    created_at: str

