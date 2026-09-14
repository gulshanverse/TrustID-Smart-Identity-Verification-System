import Link from "next/link";
import { Card } from "@/components/ui";
import { ConsolePage } from "@/components/console-page";
import { DemoModeBadge } from "@/components/status";

const scenarios = [
  ["Genuine / low risk", "Clean fictional document, consistent structured fields, and matching demo face."],
  ["Tampered document", "Technical tampering signals require officer review; no authenticity claim is made."],
  ["Face mismatch", "The deterministic demo comparison returns a mismatch signal for human review."],
  ["Expired document", "Document validation identifies an expired fictional document."],
  ["Multiple issues", "Several technical findings combine into an explainable review recommendation."],
] as const;

export default function DemoPage() {
  return (
    <ConsolePage title="SIH demonstration mode" description="Run fictional, deterministic scenarios through the real verification workflow.">
      <Card>
        <div className="analytics-demo-banner"><strong><DemoModeBadge /> DEMO MODE / SIMULATED</strong><span>Use only the fictional demo identities and documents supplied by TrustID. Real uploads are never converted into fabricated demo results.</span></div>
        <h2>Supported scenarios</h2>
        <div className="module-health-grid">
          {scenarios.map(([title, description]) => <div className="health-card" key={title}><strong>{title}</strong><span>{description}</span></div>)}
        </div>
        <p className="placeholder-note">The core path remains provider-neutral and local: upload → OCR → validation → technical tampering analysis → face comparison → explainable risk → case, audit, analytics, and report.</p>
        <Link className="button button-primary" href="/console/verify">Start a demo verification</Link>
      </Card>
    </ConsolePage>
  );
}
