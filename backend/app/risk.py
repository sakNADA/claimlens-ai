import re

from .models import ClaimCreate, RiskFactor


AMOUNT_PATTERN = re.compile(r"(?:MAD|DH|USD|EUR)?\s*([0-9][0-9\s,.]{1,14})", re.IGNORECASE)


def extract_invoice_amount(invoice_text: str) -> float | None:
    candidates: list[float] = []
    for raw in AMOUNT_PATTERN.findall(invoice_text):
        normalized = raw.replace(" ", "").replace(",", ".")
        if normalized.count(".") > 1:
            normalized = normalized.replace(".", "", normalized.count(".") - 1)
        try:
            candidates.append(float(normalized))
        except ValueError:
            continue
    return max(candidates) if candidates else None


def score_claim(payload: ClaimCreate, invoice_amount: float | None) -> tuple[int, str, list[RiskFactor]]:
    factors: list[RiskFactor] = []

    if invoice_amount is None:
        factors.append(RiskFactor(code="NO_INVOICE_TOTAL", label="Invoice total not detected", points=18, evidence="No monetary total could be extracted."))
    else:
        delta = abs(invoice_amount - payload.claimed_amount) / payload.claimed_amount
        if delta > 0.1:
            factors.append(RiskFactor(code="AMOUNT_MISMATCH", label="Claim and invoice mismatch", points=35, evidence=f"Claimed {payload.claimed_amount:.2f} MAD vs extracted {invoice_amount:.2f} MAD."))

    if payload.claimed_amount >= 50_000:
        factors.append(RiskFactor(code="HIGH_VALUE", label="High-value claim", points=22, evidence=f"Claim amount is {payload.claimed_amount:.2f} MAD."))

    if len(payload.damage_description.strip()) < 20:
        factors.append(RiskFactor(code="THIN_EVIDENCE", label="Limited damage evidence", points=15, evidence="Damage description is shorter than 20 characters."))

    suspicious_terms = {"cash only", "urgent payment", "no police report", "lost receipt"}
    combined = f"{payload.incident_description} {payload.damage_description}".lower()
    hits = sorted(term for term in suspicious_terms if term in combined)
    if hits:
        factors.append(RiskFactor(code="REVIEW_TERMS", label="Manual-review language detected", points=25, evidence=", ".join(hits)))

    score = min(100, sum(factor.points for factor in factors))
    level = "high" if score >= 60 else "medium" if score >= 30 else "low"
    return score, level, factors

