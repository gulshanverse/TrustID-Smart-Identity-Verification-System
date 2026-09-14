"use client";

import { ChangeEvent, DragEvent, useState } from "react";
import { CheckCircle2, FileText, IdCard, Plane, ScanLine, UploadCloud, X } from "lucide-react";
import { Card } from "@/components/ui";
import { ConsolePage } from "@/components/console-page";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024;
const documentTypes = [["PASSPORT", "Passport", Plane], ["VISA", "Visa", FileText], ["NATIONAL_ID", "National ID", IdCard], ["DRIVING_LICENSE", "Driving License", IdCard], ["PERMIT", "Permit", FileText]] as const;
const accepted = new Map([[".pdf", "application/pdf"], [".jpg", "image/jpeg"], [".jpeg", "image/jpeg"], [".png", "image/png"], [".webp", "image/webp"]]);
type OCRResult = { id: string; status: string; raw_text: string; language: string; overall_confidence: number; provider: string; provider_version: string; fields: { name: string; value: string; normalized_value: string; confidence: number; source_text: string; evidence?: { page?: number; line_index?: number } | null }[] };

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
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "validating" | "uploading" | "success" | "error">("idle");
  const [ocrState, setOcrState] = useState<"idle" | "processing" | "complete" | "error">("idle");
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [message, setMessage] = useState("");
  const choose = (candidate: File | undefined) => { if (!candidate) return; const error = validateFile(candidate); setMessage(error ?? ""); setFile(error ? null : candidate); setState(error ? "error" : "validating"); setDocumentId(null); setOcrResult(null); setOcrState("idle"); };
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
      const data = await response.json().catch(() => ({})) as { detail?: string; id?: string };
      if (!response.ok || !data.id) throw new Error(data.detail ?? "The document could not be uploaded.");
      setDocumentId(data.id); setState("success"); setMessage("Document uploaded successfully. Ready for OCR.");
    } catch (error) { setState("error"); setMessage(error instanceof Error ? error.message : "Upload failed. Try again."); }
  };
  const startOCR = async () => {
    if (!documentId) return;
    setOcrState("processing"); setMessage("");
    try {
      const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/ocr`, { method: "POST", credentials: "include" });
      const data = await response.json().catch(() => ({})) as OCRResult & { detail?: string };
      if (!response.ok) throw new Error(data.detail ?? "OCR processing could not be completed.");
      setOcrResult(data); setOcrState("complete");
    } catch (error) { setOcrState("error"); setMessage(error instanceof Error ? error.message : "OCR processing could not be completed."); }
  };
  return <ConsolePage title="New Verification" description="Securely ingest a document, then extract text and structured fields for future validation.">
    <div className="console-demo-banner"><strong>Phase 6 · OCR extraction</strong><span>OCR extracts text and fields only. It does not determine authenticity, fraud, or government verification.</span></div>
    <Card><div className="console-card-heading"><div><h2>Step 1 · Document type</h2><p>Select the category that matches the document.</p></div><ScanLine size={24} /></div><div className="document-type-grid">{documentTypes.map(([value, label, Icon]) => <button type="button" className={`document-type-option ${type === value ? "selected" : ""}`} key={value} onClick={() => setType(value)} aria-pressed={type === value}><Icon size={22} /><strong>{label}</strong><span>{type === value ? "Selected" : "Select"}</span></button>)}</div></Card>
    <Card><div className="console-card-heading"><div><h2>Step 2 · Upload document</h2><p>Accepted: PDF, JPG, PNG, WebP · Maximum size: 10 MB</p></div><UploadCloud size={24} /></div>
      <div className="upload-dropzone" onDragOver={(event) => event.preventDefault()} onDrop={onDrop}><UploadCloud size={30} /><strong>Drop a document here</strong><span>or use the accessible file picker below</span><label className="button button-secondary" htmlFor="document-file">Choose file</label><input id="document-file" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={onChange} /></div>
      {file && <div className="selected-file"><FileText size={20} /><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB · {file.type || "document"}</span></div><button type="button" aria-label="Remove selected file" onClick={() => { setFile(null); setState("idle"); setDocumentId(null); setOcrResult(null); setOcrState("idle"); }}><X size={18} /></button></div>}
      {state === "uploading" && <p className="upload-status" role="status">Uploading document...</p>}
      {state === "success" && <div className="upload-success" role="status"><CheckCircle2 size={22} /><div><strong>Document securely uploaded.</strong><span>Status: READY FOR ANALYSIS. Upload success does not mean the document is authentic or verified.</span></div></div>}
      {state === "error" && <div className="upload-error" role="alert"><strong>Upload failed</strong><span>{message}</span></div>}
      {state !== "success" && <button type="button" className="button button-primary upload-submit" disabled={!file || state === "uploading"} onClick={() => void upload()}>{state === "uploading" ? "Uploading..." : "Upload document"}</button>}
    </Card>
    {state === "success" && <Card><div className="console-card-heading"><div><h2>Step 3 · OCR extraction</h2><p>Run server-side OCR on the securely stored document.</p></div><ScanLine size={24} /></div>{ocrState === "idle" && <><p className="placeholder-note">The configured provider is explicitly labeled DEMO / SIMULATED and only processes marked demo fixtures.</p><button type="button" className="button button-primary" onClick={() => void startOCR()}>Start OCR</button></>}{ocrState === "processing" && <p className="upload-status" role="status">OCR PROCESSING · Extracting document text...</p>}{ocrState === "error" && <div className="upload-error" role="alert"><strong>OCR failed</strong><span>{message}</span></div>}{ocrState === "complete" && ocrResult && <div className="ocr-result" role="status"><div className="upload-success"><CheckCircle2 size={22} /><div><strong>OCR COMPLETE</strong><span>Text extracted successfully. Provider: {ocrResult.provider}. Ready for validation.</span></div></div><div className="ocr-summary"><div><span>Confidence</span><strong>{Math.round(ocrResult.overall_confidence * 100)}%</strong></div><div><span>Fields extracted</span><strong>{ocrResult.fields.length}</strong></div><div><span>Language</span><strong>{ocrResult.language}</strong></div></div><h3>Structured fields</h3><div className="ocr-fields">{ocrResult.fields.map((field) => <div className="ocr-field" key={field.name}><span>{field.name.replaceAll("_", " ")}</span><strong>{field.value}</strong><small>Field confidence: {Math.round(field.confidence * 100)}%{field.evidence?.page ? ` · Page ${field.evidence.page}` : ""}</small></div>)}</div><details className="ocr-raw"><summary>Show raw OCR text</summary><pre>{ocrResult.raw_text}</pre></details></div>}</Card>}
  </ConsolePage>;
}
