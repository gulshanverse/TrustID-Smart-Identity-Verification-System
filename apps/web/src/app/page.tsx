import { AlertTriangle, CheckCircle2, Info, ShieldCheck, XCircle } from "lucide-react";
import { DocumentCard, DocumentMetadata, DocumentPreview, EvidenceCard, EvidenceList, FindingExplanation, PageContainer, Progress, PublicFooter, PublicHeader, RiskScore, SectionHeader, StatePanel, TamperingStatus, VerificationStatus } from "@/components";

export default function HomePage() {
  return <>
    <PublicHeader />
    <section className="foundation-hero">
      <div className="eyebrow">TRUSTID DESIGN SYSTEM · PHASE 1</div>
      <h1>Verify. Detect. Protect.</h1>
      <p>A calm, evidence-first interface foundation for authorized personnel. This showcase demonstrates the reusable visual language and component conventions that later TrustID experiences will use.</p>
    </section>
    <PageContainer>
      <SectionHeader eyebrow="Visual foundation" title="Hide complexity. Never hide evidence." description="TrustID prioritizes what happened, document validity, identity, tampering, risk, reasons, evidence, and the recommended next action—without presenting presentation components as an AI decision." />
      <div className="showcase-grid">
        <div className="showcase-section"><h3>Trust and status language</h3><div className="card"><div className="showcase-section"><VerificationStatus verified /><div className="status-legend"><span><CheckCircle2 size={15} /> Verified</span><span><AlertTriangle size={15} /> Review</span><span><XCircle size={15} /> High risk</span><span><Info size={15} /> Information</span></div><TamperingStatus clear /><Progress value={82} label="Confidence indicator" /></div></div></div>
        <div className="showcase-section"><h3>Explainable risk presentation</h3><RiskScore score={8} level="LOW" reasons={["Document fields are internally consistent", "No suspicious tampering signals returned"]} /></div>
        <div className="showcase-section"><h3>Document presentation</h3><DocumentCard type="Passport" filename="passport-sample-demo.jpg" status="VALID" /><DocumentPreview /><DocumentMetadata items={[{ label: "Document type", value: "Passport" }, { label: "Environment", value: "Demo data" }, { label: "Source", value: "Simulated upload" }, { label: "Evidence", value: "Available later" }]} /></div>
        <div className="showcase-section"><h3>Evidence presentation</h3><EvidenceList><EvidenceCard title="Field consistency" description="The extracted identity fields can be presented with a clear explanation and source region when analysis is available." region="Page 1 · identity block" /><FindingExplanation title="Metadata review" explanation="This is a presentation-only finding card. Real computer vision evidence is deliberately deferred to a later phase." confidence={64} severity="LOW" /></EvidenceList></div>
        <div className="showcase-section showcase-wide"><h3>Loading, empty, warning, and error patterns</h3><div className="split"><StatePanel state="loading" title="Loading verification..." description="The next status will be shown from the verification API." /><StatePanel state="empty" title="No verification records yet." description="Start a verification when the workflow phase is enabled." /><StatePanel state="warning" title="Additional review required." description="A review state is not a fraud determination." /><StatePanel state="error" title="We couldn't complete this operation." description="Try again or contact an administrator if the problem persists." /></div></div>
        <div className="showcase-section showcase-wide"><h3>System conventions</h3><div className="card"><div className="split"><div><p className="label">Secure by design</p><p><ShieldCheck size={16} /> Evidence is presented separately from recommendations, and demo/simulated states remain visibly distinct.</p></div><div><p className="label">Keyboard and contrast ready</p><p>Interactive foundations use semantic elements, visible focus states, readable contrast, and labels that do not rely on color alone.</p></div></div></div></div>
      </div>
    </PageContainer>
    <PublicFooter />
  </>;
}
