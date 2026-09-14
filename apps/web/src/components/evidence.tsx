import { AlertTriangle, MapPin, ScanSearch } from "lucide-react";
import { Card, CardHeader } from "./ui";
import { ConfidenceIndicator, EvidenceBadge } from "./status";

export function EvidenceIndicator({ count = 0 }: { count?: number }) { return <span className="evidence-indicator"><ScanSearch size={15} /> {count} evidence {count === 1 ? "item" : "items"}</span>; }
export function EvidenceRegion({ label = "Evidence region" }: { label?: string }) { return <div className="evidence-region"><MapPin size={14} /> {label}</div>; }
export function FindingSeverity({ severity }: { severity: "LOW" | "MEDIUM" | "HIGH" }) { return <span className={`finding-severity severity-${severity.toLowerCase()}`}><AlertTriangle size={14} /> {severity} severity</span>; }
export function FindingExplanation({ title, explanation, confidence = 0, severity = "LOW" }: { title: string; explanation: string; confidence?: number; severity?: "LOW" | "MEDIUM" | "HIGH" }) { return <Card className="finding-card"><CardHeader title={title} action={<FindingSeverity severity={severity} />} /><p>{explanation}</p><div className="finding-footer"><ConfidenceIndicator value={confidence} /><EvidenceBadge /></div></Card>; }
export function EvidenceCard({ title, description, region }: { title: string; description: string; region?: string }) { return <Card className="evidence-card"><CardHeader title={title} action={<EvidenceBadge />} /><p>{description}</p>{region && <EvidenceRegion label={region} />}</Card>; }
export function EvidenceList({ children }: { children: React.ReactNode }) { return <div className="evidence-list">{children}</div>; }
