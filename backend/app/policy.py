import json
import re
from functools import lru_cache
from pathlib import Path

from .models import Citation, GroundedAnswer


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]{3,}")


@lru_cache(maxsize=1)
def load_clauses() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "data" / "policies" / "motor_policy.json"
    return json.loads(path.read_text(encoding="utf-8"))["clauses"]


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def answer_policy_question(question: str) -> GroundedAnswer:
    query_tokens = _tokens(question)
    ranked = []
    for clause in load_clauses():
        clause_tokens = _tokens(f"{clause['title']} {clause['text']}")
        overlap = len(query_tokens & clause_tokens)
        relevance = overlap / max(1, len(query_tokens))
        if overlap:
            ranked.append((relevance, clause))
    ranked.sort(key=lambda item: item[0], reverse=True)
    top = ranked[:2]

    if not top:
        return GroundedAnswer(answer="The supplied policy does not contain enough evidence to answer that question. A human reviewer should check the full contract.", citations=[], grounded=False)

    citations = [
        Citation(
            clause_id=clause["id"],
            title=clause["title"],
            excerpt=clause["text"],
            relevance=round(score, 2),
        )
        for score, clause in top
    ]
    titles = ", ".join(citation.title for citation in citations)
    return GroundedAnswer(
        answer=f"The relevant policy evidence is in {titles}. The claim should be assessed against these clauses, and uncertain cases should be escalated for human review.",
        citations=citations,
        grounded=True,
    )

