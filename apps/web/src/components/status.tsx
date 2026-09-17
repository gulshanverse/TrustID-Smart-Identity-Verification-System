import { AlertTriangle, CheckCircle2, CircleHelp, FileCheck2, ShieldCheck, UserCheck, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "./ui";

const processingLabels: Record<string, string> = { CREATED: "Created", UPLOADED: "Uploaded", QUALITY_CHECK: "Quality check", OCR_PROCESSING: "OCR processing", VALIDATING: "Validating", TAMPERING_ANALYSIS: "Tampering analysis", FACE_VERIFICATION: "Face verification", RISK_ASSESSMENT: "Risk assessment", COMPLETED: "Completed", PARTIAL: "Partial evidence", FAILED: "Failed", ERROR: "Error", UNKNOWN: "Unknown", NOT_AVAILABLE: "Not available", REQUIRES_REVIEW: "Requires review", CANCELLED: "Cancelled" };

export function TrustIDLogo({ compact = false }: { compact?: boolean }) {
  return <div className="brand" aria-label="TrustID — Smart Identity Verification"><span className="brand-mark"><ShieldCheck size={20} strokeWidth={2.2} /></span>{!compact && <span><strong>TrustID</strong><small>Smart Identity Verification</small></span>}</div>;
}

export function DemoModeBadge() { return <Badge tone="warning">DEMO MODE · SIMULATED</Badge>; }

export function StatusBadge({ status, label }: { status: "verified" | "review" | "danger" | "neutral" | "info"; label: string }) {
  const Icon = status === "verified" ? CheckCircle2 : status === "review" ? AlertTriangle : status === "danger" ? XCircle : status === "info" ? CircleHelp : FileCheck2;
  return <span className={`status-badge status-${status}`}><Icon size={15} aria-hidden="true" />{label}</span>;
}

export function ProcessingStatus({ state }: { state: string }) { return <StatusBadge status={state === "COMPLETED" ? "verified" : state === "FAILED" || state === "ERROR" ? "danger" : state === "REQUIRES_REVIEW" || state === "PARTIAL" ? "review" : "info"} label={processingLabels[state] ?? state} />; }

export function RiskBadge({ level }: { level: "LOW" | "REVIEW" | "HIGH" }) { return <StatusBadge status={level === "LOW" ? "verified" : level === "REVIEW" ? "review" : "danger"} label={`${level} RISK`} />; }

export function RiskScore({ score, level, reasons }: { score: number; level: "LOW" | "REVIEW" | "HIGH"; reasons?: string[] }) {
  return <div className="risk-score"><div className="risk-score-top"><div><span className="label">RISK ASSESSMENT</span><strong>{String(score).padStart(2, "0")} <small>/ 100</small></strong></div><RiskBadge level={level} /></div>{reasons && <ul>{reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}</div>;
}

export function DocumentStatus({ status }: { status: "VALID" | "INVALID" | "EXPIRED" | "UNKNOWN" | "REQUIRES_REVIEW" }) { return <StatusBadge status={status === "VALID" ? "verified" : status === "EXPIRED" || status === "INVALID" ? "danger" : status === "REQUIRES_REVIEW" ? "review" : "neutral"} label={status.replaceAll("_", " ")} />; }
export function FaceMatchStatus({ status }: { status: "MATCH" | "NO_MATCH" | "COULD_NOT_VERIFY" | "NOT_AVAILABLE" }) { return <StatusBadge status={status === "MATCH" ? "verified" : status === "NO_MATCH" ? "danger" : "review"} label={status.replaceAll("_", " ")} />; }
export function TamperingStatus({ clear }: { clear: boolean }) { return <StatusBadge status={clear ? "verified" : "review"} label={clear ? "TAMPERING CLEAR" : "REVIEW REQUIRED"} />; }
export function ConfidenceIndicator({ value }: { value: number }) { return <span className="confidence" aria-label={`${value}% confidence`}><span style={{ width: `${value}%` }} />{value}% confidence</span>; }
export function EvidenceBadge({ children = "Evidence available" }: { children?: ReactNode }) { return <Badge tone="info">▣ {children}</Badge>; }
export function OfficerDecisionBadge({ decision }: { decision: "APPROVE" | "REVIEW" | "REJECT" }) { return <Badge tone={decision === "APPROVE" ? "success" : decision === "REVIEW" ? "warning" : "danger"}>{decision}</Badge>; }
export function VerificationStatus({ verified }: { verified: boolean }) { return <StatusBadge status={verified ? "verified" : "review"} label={verified ? "✓ VERIFIED" : "ADDITIONAL REVIEW"} />; }
export function IdentityStatus({ matched }: { matched: boolean }) { return <StatusBadge status={matched ? "verified" : "danger"} label={matched ? "IDENTITY MATCHED" : "IDENTITY MISMATCH"} />; }
export function StatusLegend() { return <div className="status-legend"><span><CheckCircle2 size={15} /> Verified</span><span><AlertTriangle size={15} /> Review</span><span><XCircle size={15} /> High risk</span><CircleHelp size={15} /> Information</div>; }
