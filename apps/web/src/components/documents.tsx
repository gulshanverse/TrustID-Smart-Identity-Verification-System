import { FileText, Image as ImageIcon, ScanLine } from "lucide-react";
import { Badge, Card, CardHeader } from "./ui";
import { DocumentStatus } from "./status";

export function DocumentTypeBadge({ type }: { type: string }) { return <Badge tone="neutral"><FileText size={13} /> {type}</Badge>; }
export function DocumentCard({ type, filename, status }: { type: string; filename: string; status: "VALID" | "INVALID" | "EXPIRED" | "UNKNOWN" | "REQUIRES_REVIEW" }) { return <Card className="document-card"><CardHeader title={filename} description="Document record" action={<DocumentStatus status={status} />} /><div className="document-meta"><DocumentTypeBadge type={type} /><span>Uploaded for analysis</span></div></Card>; }
export function DocumentPreview({ label = "Document preview" }: { label?: string }) { return <div className="document-preview" aria-label={label}><div className="preview-grid"><ImageIcon size={30} /><span>{label}</span><small>Evidence region rendering will be added in a later phase.</small></div></div>; }
export function DocumentThumbnail({ type }: { type: string }) { return <div className="document-thumbnail"><ScanLine size={20} /><span>{type}</span></div>; }
export function DocumentMetadata({ items }: { items: Array<{ label: string; value: string }> }) { return <dl className="document-metadata">{items.map(({ label, value }) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>; }
