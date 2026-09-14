"use client";

import { ChangeEvent, DragEvent, useState } from "react";
import { CheckCircle2, FileText, IdCard, Plane, ScanLine, UploadCloud, X } from "lucide-react";
import { Card } from "@/components/ui";
import { ConsolePage } from "@/components/console-page";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024;
const documentTypes = [["PASSPORT", "Passport", Plane], ["VISA", "Visa", FileText], ["NATIONAL_ID", "National ID", IdCard], ["DRIVING_LICENSE", "Driving License", IdCard], ["PERMIT", "Permit", FileText]] as const;
const accepted = new Map([[".pdf", "application/pdf"], [".jpg", "image/jpeg"], [".jpeg", "image/jpeg"], [".png", "image/png"], [".webp", "image/webp"]]);

function validateFile(file: File): string | null {
  const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
  if (!accepted.has(extension)) return "Unsupported document type. Use PDF, JPG, PNG, or WebP.";
  if (file.type && file.type !== accepted.get(extension)) return "The file type does not match its declared content type.";
  if (!file.size) return "The selected file is empty.";
  if (file.size > MAX_DOCUMENT_SIZE_BYTES) return "The document exceeds the 10 MB maximum size.";
  return null;
}

export default function VerifyPage() {
  const [type, setType] = useState("PASSPORT");
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<"idle" | "validating" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const choose = (candidate: File | undefined) => { if (!candidate) return; const error = validateFile(candidate); setMessage(error ?? ""); setFile(error ? null : candidate); setState(error ? "error" : "validating"); };
  const onDrop = (event: DragEvent<HTMLDivElement>) => { event.preventDefault(); choose(event.dataTransfer.files[0]); };
  const onChange = (event: ChangeEvent<HTMLInputElement>) => choose(event.target.files?.[0]);
  const upload = async () => {
    if (!file) return;
    setState("uploading"); setMessage("");
    try {
      const verification = await fetch(`${API_URL}/api/v1/verifications`, { method: "POST", credentials: "include" });
      if (!verification.ok) throw new Error("Unable to start a verification.");
      const { id } = await verification.json() as { id: string };
      const body = new FormData(); body.append("document_type", type); body.append("file", file);
      const response = await fetch(`${API_URL}/api/v1/verifications/${id}/documents`, { method: "POST", credentials: "include", body });
      const data = await response.json().catch(() => ({})) as { detail?: string };
      if (!response.ok) throw new Error(data.detail ?? "The document could not be uploaded.");
      setState("success"); setMessage("Document uploaded successfully. Ready for document analysis.");
    } catch (error) { setState("error"); setMessage(error instanceof Error ? error.message : "Upload failed. Try again."); }
  };
  return <ConsolePage title="New Verification" description="Securely ingest an identity document for the future evidence-oriented analysis workflow.">
    <div className="console-demo-banner"><strong>Phase 5 · Document ingestion</strong><span>Files are validated and securely stored. No OCR, authenticity, or fraud decision is performed yet.</span></div>
    <Card><div className="console-card-heading"><div><h2>Step 1 · Document type</h2><p>Select the category that matches the document.</p></div><ScanLine size={24} /></div><div className="document-type-grid">{documentTypes.map(([value, label, Icon]) => <button type="button" className={`document-type-option ${type === value ? "selected" : ""}`} key={value} onClick={() => setType(value)} aria-pressed={type === value}><Icon size={22} /><strong>{label}</strong><span>{type === value ? "Selected" : "Select"}</span></button>)}</div></Card>
    <Card><div className="console-card-heading"><div><h2>Step 2 · Upload document</h2><p>Accepted: PDF, JPG, PNG, WebP · Maximum size: 10 MB</p></div><UploadCloud size={24} /></div>
      <div className="upload-dropzone" onDragOver={(event) => event.preventDefault()} onDrop={onDrop}><UploadCloud size={30} /><strong>Drop a document here</strong><span>or use the accessible file picker below</span><label className="button button-secondary" htmlFor="document-file">Choose file</label><input id="document-file" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={onChange} /></div>
      {file && <div className="selected-file"><FileText size={20} /><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB · {file.type || "document"}</span></div><button type="button" aria-label="Remove selected file" onClick={() => { setFile(null); setState("idle"); }}><X size={18} /></button></div>}
      {state === "uploading" && <p className="upload-status" role="status">Uploading document...</p>}
      {state === "success" && <div className="upload-success" role="status"><CheckCircle2 size={22} /><div><strong>Document uploaded successfully.</strong><span>Ready for document analysis. This does not mean the document is authentic or verified.</span></div></div>}
      {state === "error" && <div className="upload-error" role="alert"><strong>Upload failed</strong><span>{message}</span></div>}
      {state !== "success" && <button type="button" className="button button-primary upload-submit" disabled={!file || state === "uploading"} onClick={() => void upload()}>{state === "uploading" ? "Uploading..." : "Upload document"}</button>}
    </Card>
  </ConsolePage>;
}
