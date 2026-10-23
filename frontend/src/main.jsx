import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, AlertTriangle, FileCheck2, Plus, Search, ShieldCheck } from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const sample = {
  claimant: "Amal Benali",
  policy_number: "POL-AUTO-2048",
  incident_description: "Rear bumper damaged in a low-speed collision on a public road.",
  damage_description: "Visible bumper crack and damaged parking sensor on the left side.",
  claimed_amount: 12500,
  invoice_text: "Repair estimate TOTAL MAD 12 500.00",
};

function App() {
  const [claims, setClaims] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [question, setQuestion] = useState("Is accidental collision damage covered?");
  const [answer, setAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const response = await fetch(`${API}/api/claims`);
      if (!response.ok) throw new Error("API unavailable");
      const data = await response.json();
      setClaims(data);
      if (!selected && data.length) setSelected(data[0]);
      setError("");
    } catch {
      setError("Start the API on port 8000 to load claims.");
    }
  };

  useEffect(() => { refresh(); }, []);

  const filtered = useMemo(() => claims.filter((claim) =>
    `${claim.claimant} ${claim.policy_number}`.toLowerCase().includes(query.toLowerCase())
  ), [claims, query]);

  const createSample = async () => {
    setBusy(true);
    const response = await fetch(`${API}/api/claims`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sample),
    });
    const created = await response.json();
    setSelected(created);
    await refresh();
    setBusy(false);
  };

  const askPolicy = async () => {
    setBusy(true);
    const response = await fetch(`${API}/api/policy/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    setAnswer(await response.json());
    setBusy(false);
  };

  const metrics = {
    total: claims.length,
    high: claims.filter((c) => c.risk_level === "high").length,
    review: claims.filter((c) => c.status === "review").length,
  };

  return (
    <div className="shell">
      <aside>
        <div className="brand"><ShieldCheck size={28} /><div><strong>ClaimLens AI</strong><span>Claims intelligence</span></div></div>
        <nav><button className="active"><Activity size={18} /> Operations</button><button><FileCheck2 size={18} /> Policy evidence</button></nav>
        <div className="system"><span className="status-dot" /> Synthetic data mode</div>
      </aside>

      <main>
        <header>
          <div><p className="eyebrow">Claims operations</p><h1>Review queue</h1></div>
          <button className="primary" onClick={createSample} disabled={busy}><Plus size={18} /> Add sample claim</button>
        </header>

        <section className="metrics">
          <div><span>Total claims</span><strong>{metrics.total}</strong></div>
          <div><span>Awaiting review</span><strong>{metrics.review}</strong></div>
          <div><span>High risk</span><strong>{metrics.high}</strong></div>
        </section>

        {error && <div className="notice"><AlertTriangle size={18} /> {error}</div>}

        <div className="workspace">
          <section className="queue">
            <div className="section-head"><h2>Incoming claims</h2><label><Search size={17} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search" /></label></div>
            <div className="table-head"><span>Claimant</span><span>Amount</span><span>Risk</span></div>
            {filtered.length === 0 && <p className="empty">No claims yet. Add the synthetic sample to begin.</p>}
            {filtered.map((claim) => <button className={`claim-row ${selected?.id === claim.id ? "selected" : ""}`} key={claim.id} onClick={() => setSelected(claim)}>
              <span><strong>{claim.claimant}</strong><small>{claim.policy_number}</small></span>
              <span>{claim.claimed_amount.toLocaleString()} MAD</span>
              <span className={`risk ${claim.risk_level}`}>{claim.risk_score} · {claim.risk_level}</span>
            </button>)}
          </section>

          <section className="detail">
            <p className="eyebrow">Decision support</p>
            {!selected ? <p className="empty">Select a claim to inspect its evidence.</p> : <>
              <h2>{selected.claimant}</h2>
              <div className="facts"><div><span>Claimed</span><strong>{selected.claimed_amount.toLocaleString()} MAD</strong></div><div><span>Invoice extracted</span><strong>{selected.extracted_invoice_amount?.toLocaleString() || "Not found"} MAD</strong></div></div>
              <h3>Explainable risk factors</h3>
              {selected.risk_factors.length ? selected.risk_factors.map((factor) => <div className="factor" key={factor.code}><AlertTriangle size={17} /><div><strong>{factor.label} (+{factor.points})</strong><p>{factor.evidence}</p></div></div>) : <div className="factor clear"><ShieldCheck size={17} /><div><strong>No material risk flags</strong><p>The submitted values are internally consistent.</p></div></div>}
              <h3>Policy assistant</h3>
              <div className="ask"><input value={question} onChange={(e) => setQuestion(e.target.value)} /><button onClick={askPolicy} disabled={busy}>Ask</button></div>
              {answer && <div className="answer"><p>{answer.answer}</p>{answer.citations.map((citation) => <blockquote key={citation.clause_id}><strong>{citation.clause_id} · {citation.title}</strong>{citation.excerpt}</blockquote>)}</div>}
            </>}
          </section>
        </div>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
