"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { ConsolePage } from "@/components/console-page";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Evidence = { evidence_id: string; source_module: string; evidence_type: string; status: string; severity: string; confidence?: number | null; score?: number | null; explanation: string; reason_code: string; provenance: { module: string; provider: string; version: string; rule?: string | null } };
type Finding = { finding_id: string; code: string; status: string; severity: string; title: string; explanation: string; risk_contribution: number; provenance: { module: string; provider: string; version: string; rule?: string | null } };
type Result = { correlation_summary: string; evidence: Evidence[]; findings: Finding[]; risk: { risk_score: number; risk_level: string; recommendation: string } };

export default function InvestigationPage() {
  const [verificationId, setVerificationId] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [message, setMessage] = useState("");
  const load = async () => {
    if (!verificationId.trim()) return;
    setMessage("");
    try {
      const response = await fetch(`${API_URL}/api/v1/verifications/${verificationId.trim()}/result`, { credentials: "include" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Evidence result is unavailable.");
      setResult(data as Result);
    } catch (error) {
      setResult(null);
      setMessage(error instanceof Error ? error.message : "Evidence result is unavailable.");
    }
  };
  return <ConsolePage title="Evidence investigation" description="Review normalized evidence, contradictions, provenance, and risk contributions from an authorized verification.">
    <Card><div className="case-search"><input aria-label="Verification ID" value={verificationId} onChange={(event) => setVerificationId(event.target.value)} placeholder="Verification ID" /><button className="button button-primary" type="button" onClick={() => void load()}>Load evidence</button></div><p className="placeholder-note">Sensitive values are not repeated here. The view exposes source, rule, status, severity, and explanation for authorized review.</p>{message && <div className="upload-error" role="alert">{message}</div>}</Card>
    {result && <><Card><div className="case-header"><div><span className="eyebrow">Correlation summary</span><h2>{result.correlation_summary}</h2><p>{result.risk.recommendation}</p></div><span className={`case-pill priority-${result.risk.risk_level.toLowerCase()}`}>Risk {result.risk.risk_score} · {result.risk.risk_level}</span></div></Card><Card><h2>Verification findings</h2>{result.findings.length === 0 ? <p className="placeholder-note">No contradictions or elevated findings were produced.</p> : <div className="case-evidence-list">{result.findings.map((finding) => <article key={finding.finding_id}><div><strong>{finding.title} · {finding.code}</strong><span>{finding.severity} · risk contribution {finding.risk_contribution}</span></div><p>{finding.explanation}</p><small>Source: {finding.provenance.module} · {finding.provenance.provider} {finding.provenance.version}{finding.provenance.rule ? ` · rule ${finding.provenance.rule}` : ""}</small></article>)}</div>}</Card><Card><h2>Normalized evidence</h2><div className="case-table-wrap"><table className="case-table"><thead><tr><th>Module</th><th>Type</th><th>Status</th><th>Severity</th><th>Reason</th><th>Provenance</th></tr></thead><tbody>{result.evidence.map((item) => <tr key={item.evidence_id}><td>{item.source_module}</td><td>{item.evidence_type}</td><td>{item.status}</td><td>{item.severity}</td><td>{item.reason_code}</td><td>{item.provenance.provider} {item.provenance.version}</td></tr>)}</tbody></table></div></Card></>}
  </ConsolePage>;
}
