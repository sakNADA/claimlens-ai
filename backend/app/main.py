import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .database import ClaimRepository
from .models import AuditEvent, Claim, ClaimCreate, DecisionRequest, GroundedAnswer, QuestionRequest
from .policy import answer_policy_question


repository = ClaimRepository()


@asynccontextmanager
async def lifespan(_: FastAPI):
    repository.init_schema()
    yield


app = FastAPI(
    title="ClaimLens AI",
    version="0.1.0",
    description="Explainable claims intelligence API using synthetic data.",
    lifespan=lifespan,
)

origins = [origin.strip() for origin in os.getenv("CLAIMLENS_CORS_ORIGINS", "http://localhost:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "claimlens-api", "version": app.version}


@app.get("/api/claims", response_model=list[Claim])
def list_claims():
    return repository.list()


@app.post("/api/claims", response_model=Claim, status_code=201)
def create_claim(payload: ClaimCreate):
    return repository.create(payload)


@app.get("/api/claims/{claim_id}", response_model=Claim)
def get_claim(claim_id: str):
    claim = repository.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@app.post("/api/claims/{claim_id}/decision", response_model=Claim)
def decide_claim(claim_id: str, payload: DecisionRequest):
    claim = repository.decide(claim_id, payload)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@app.get("/api/claims/{claim_id}/audit", response_model=list[AuditEvent])
def claim_audit(claim_id: str):
    if not repository.get(claim_id):
        raise HTTPException(status_code=404, detail="Claim not found")
    return repository.audit(claim_id)


@app.post("/api/policy/ask", response_model=GroundedAnswer)
def ask_policy(payload: QuestionRequest):
    return answer_policy_question(payload.question)

