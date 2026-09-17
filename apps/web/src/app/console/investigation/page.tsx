"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { ConsolePage } from "@/components/console-page";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Evidence = { evidence_id: string; source_module: string; evidence_type: string; status: string; severity: string; confidence?: number | null; score?: number | null; explanation: string; reason_code: string; provenance: { module: string; provider: string; version: string; rule?: string | null } };
type Finding = { finding_id: string; code: string; status: string; severity: string; title: string; explanation: string; risk_contribution: number; provenance: { module: string; provider: string; version: string; rule?: string | null } };
type Intelligence = { status: string; version: string; evidence_summary: { evidence_id: string; category: string; source: string; status: string; severity: string; explanation: string; provider: string; version: string; rule_id?: string | null }[]; contradictions: { code: string; severity: string; explanation: string }[]; review_priorities: { priority: string; code: string; explanation: string }[]; missing_information: { code: string; status: string; explanation: string }[]; risk_context: { score: number; band: string; assessment_version: string; factors: { factor: string; contribution: number; explanation: string; provenance: string }[] } };
type Result = { status: string; correlation_summary: string; evidence: Evidence[]; findings: Finding[]; risk: { risk_score: number; risk_level: string; recommendation: string }; intelligence?: Intelligence };

export default function InvestigationPage() {
  const [verificationId, setVerificationId] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [message, setMessage] = useState("");
  const load = async () => {
    if (!verificationId.trim()) return;
    setMessage("");
    try {
      const id = verificationId.trim();
      const [response, intelligenceResponse] = await Promise.all([fetch(`${API_URL}/api/v1/verifications/${id}/result`, { credentials: "include" }), fetch(`${API_URL}/api/v1/verifications/${id}/decision-intelligence`, { credentials: "include" })]);
      const data = await response.json().catch(() => ({}));
      const intelligence = await intelligenceResponse.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Evidence result is unavailable.");
      setResult({ ...data, intelligence: intelligenceResponse.ok ? intelligence : undefined } as Result);
      if (!intelligenceResponse.ok) setMessage("Decision Intelligence is unavailable because analysis is incomplete.");
    } catch (error) {
      setResult(null);
      setMessage(error instanceof Error ? error.message : "Evidence result is unavailable.");
    }
  };
  return <ConsolePage title="Evidence investigation" description="Review normalized evidence, contradictions, provenance, and risk contributions from an authorized verification.">
    <Card><div className="case-search"><input aria-label="Verification ID" value={verificationId} onChange={(event) => setVerificationId(event.target.value)} placeholder="Verification ID" /><button className="button button-primary" type="button" onClick={() => void load()}>Load evidence</button></div><p className="placeholder-note">Decision Intelligence explains evidence for authorized officer review. It does not determine identity, fraud, legal status, or the final decision.</p>{message && <div className="upload-error" role="alert">{message}</div>}</Card>
    {result && <>{result.intelligence && <Card><h2>Decision Intelligence</h2><p className="placeholder-note">{result.intelligence.version} · {result.intelligence.status}</p><div className="case-header"><div><span className="eyebrow">Review priorities</span><h2>{result.intelligence.review_priorities.length} evidence-derived priorities</h2><p>Workflow guidance only; the officer remains the decision-maker.</p></div><span className={`case-pill priority-${result.intelligence.risk_context.band.toLowerCase()}`}>Risk {result.intelligence.risk_context.score} · {result.intelligence.risk_context.band}</span></div><div className="case-evidence-list">{result.intelligence.review_priorities.map((item) => <article key={item.code}><strong>{item.priority} · {item.code}</strong><p>{item.explanation}</p></article>)}</div><h3>Missing information</h3><ul>{result.intelligence.missing_information.map((item) => <li key={item.code}>{item.status} · {item.explanation}</li>)}</ul><h3>Contradictions</h3>{result.intelligence.contradictions.length === 0 ? <p className="placeholder-note">No source contradiction was detected.</p> : <div className="case-evidence-list">{result.intelligence.contradictions.map((item) => <article key={item.code}><strong>{item.severity} · {item.code}</strong><p>{item.explanation}</p></article>)}</div>}<h3>Evidence summary</h3><div className="case-table-wrap"><table className="case-table"><thead><tr><th>Category</th><th>Source</th><th>Status</th><th>Severity</th><th>Provenance</th></tr></thead><tbody>{result.intelligence.evidence_summary.map((item) => <tr key={item.evidence_id}><td>{item.category}</td><td>{item.source}</td><td>{item.status}</td><td>{item.severity}</td><td>{item.provider} {item.version}{item.rule_id ? ` · ${item.rule_id}` : ""}</td></tr>)}</tbody></table></div></Card>}<Card><div className="case-header"><div><span className="eyebrow">Correlation summary · {result.status}</span><h2>{result.correlation_summary}</h2><p>{result.risk.recommendation}</p></div><span className={`case-pill priority-${result.risk.risk_level.toLowerCase()}`}>Risk {result.risk.risk_score} · {result.risk.risk_level}</span></div>{result.status === "PARTIAL" && <p className="placeholder-note">Partial evidence: unavailable modules remain explicitly listed below and require officer review where applicable.</p>}</Card><Card><h2>Verification findings</h2>{result.findings.length === 0 ? <p className="placeholder-note">No contradictions or elevated findings were produced.</p> : <div className="case-evidence-list">{result.findings.map((finding) => <article key={finding.finding_id}><div><strong>{finding.title} · {finding.code}</strong><span>{finding.severity} · risk contribution {finding.risk_contribution}</span></div><p>{finding.explanation}</p><small>Source: {finding.provenance.module} · {finding.provenance.provider} {finding.provenance.version}{finding.provenance.rule ? ` · rule ${finding.provenance.rule}` : ""}</small></article>)}</div>}</Card><Card><h2>Normalized evidence</h2><div className="case-table-wrap"><table className="case-table"><thead><tr><th>Module</th><th>Type</th><th>Status</th><th>Severity</th><th>Reason</th><th>Provenance</th></tr></thead><tbody>{result.evidence.map((item) => <tr key={item.evidence_id}><td>{item.source_module}</td><td>{item.evidence_type}</td><td>{item.status}</td><td>{item.severity}</td><td>{item.reason_code}</td><td>{item.provenance.provider} {item.provenance.version}</td></tr>)}</tbody></table></div></Card></>}
  </ConsolePage>;
}
