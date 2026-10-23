from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def sample_claim(**overrides):
    payload = {
        "claimant": "Amal Benali",
        "policy_number": "POL-AUTO-2048",
        "incident_description": "Rear bumper damaged in a low-speed collision on a public road.",
        "damage_description": "Visible bumper crack and damaged parking sensor on the left side.",
        "claimed_amount": 12500,
        "invoice_text": "Repair estimate TOTAL MAD 12 500.00",
    }
    payload.update(overrides)
    return payload


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_local_dashboard_origin_is_allowed():
    response = client.options(
        "/api/claims",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_create_low_risk_claim_and_audit():
    response = client.post("/api/claims", json=sample_claim())
    assert response.status_code == 201
    claim = response.json()
    assert claim["risk_level"] == "low"
    assert claim["extracted_invoice_amount"] == 12500

    audit = client.get(f"/api/claims/{claim['id']}/audit")
    assert audit.status_code == 200
    assert audit.json()[0]["event_type"] == "CLAIM_CREATED"


def test_amount_mismatch_is_explainable():
    response = client.post("/api/claims", json=sample_claim(invoice_text="TOTAL MAD 29 900"))
    claim = response.json()
    codes = {factor["code"] for factor in claim["risk_factors"]}
    assert "AMOUNT_MISMATCH" in codes
    assert claim["risk_score"] >= 35


def test_policy_answer_contains_citation():
    response = client.post("/api/policy/ask", json={"question": "Is accidental collision damage covered?"})
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["citations"]


def test_decision_is_recorded():
    claim = client.post("/api/claims", json=sample_claim()).json()
    response = client.post(
        f"/api/claims/{claim['id']}/decision",
        json={"decision": "approved", "reviewer": "Nada", "note": "Evidence and amounts are consistent."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    audit = client.get(f"/api/claims/{claim['id']}/audit").json()
    assert audit[0]["event_type"] == "DECISION_RECORDED"

