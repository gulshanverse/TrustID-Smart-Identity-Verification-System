import { FileText, IdCard, Plane, ScanLine } from "lucide-react";
import { Card } from "@/components/ui";
import { ConsolePage } from "@/components/console-page";
import { DemoModeBadge } from "@/components/status";

const documentTypes = [["Passport", Plane], ["Visa", FileText], ["National ID", IdCard], ["Driving License", IdCard], ["Permit", FileText]] as const;
export default function VerifyPage() { return <ConsolePage title="New Verification" description="Prepare a document for a future evidence-oriented screening workflow."><div className="console-demo-banner"><DemoModeBadge /><span>Verification workflow coming in the next phase. No files are uploaded or processed here.</span></div><Card><div className="console-card-heading"><div><h2>Select document type</h2><p>Choose the document category you intend to screen when the workflow is enabled.</p></div><ScanLine size={24} /></div><div className="document-type-grid">{documentTypes.map(([label, Icon]) => <div className="document-type-option" key={label}><Icon size={22} /><strong>{label}</strong><span>Coming soon</span></div>)}</div><p className="placeholder-note">Preparation guidance: have a clear, complete document image available and follow your organization&apos;s handling policy.</p></Card></ConsolePage>; }
