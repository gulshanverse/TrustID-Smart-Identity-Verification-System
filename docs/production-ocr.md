# Production OCR and Document Intelligence

TrustID now supports two explicit OCR modes selected by `OCR_PROVIDER`.

`demo` preserves the existing deterministic fictional fixture provider. It accepts only TrustID-marked demo documents and remains the default for the SIH demonstration workflow.

`production` uses a local Tesseract adapter through `pytesseract`. The adapter accepts supported uploaded PDFs and images without TrustID demo markers, applies bounded quality assessment, extracts OCR text conservatively, detects and parses passport TD3 MRZ candidates, validates ICAO check digits, and reports visual OCR versus MRZ consistency. Missing fields remain absent; the adapter does not invent identity values.

The API remains provider-neutral: `OCRService` depends on `OCRProvider`, while provider selection is isolated in the OCR route factory. Results persist quality, MRZ, and consistency metadata in JSON columns and expose them through the backward-compatible OCR response.

## Quality and safety boundary

Image quality uses Pillow dimensions, bounded pixel count, brightness, contrast, and a readiness score. PDF quality uses `pypdf`, limits processing to five pages, and reports whether extractable text is available. PDF OCR rendering is bounded to five pages and uses `pdf2image` at a controlled resolution. Existing upload limits, MIME checks, magic signatures, private storage, and safe keys remain unchanged.

Production OCR requires the `pytesseract`, Pillow, `pypdf`, and `pdf2image` Python packages plus the host `tesseract` and PDF rendering binaries. If the engine or its runtime dependencies are absent, production OCR fails clearly with a safe 503 response; it never silently falls back to demo mode.

The current Render free backend should keep `OCR_PROVIDER=demo` unless Tesseract and Poppler are explicitly provisioned and memory usage has been validated. A clean zero-cost deployment option is a separately provisioned CPU OCR worker running the same provider boundary, with the TrustID API retaining authentication, storage, persistence, and orchestration. No document is sent to an external AI API by default.

## Interpretation

Quality, OCR confidence, MRZ validity, checksum failures, and field mismatches are evidence signals for review. They are not authenticity proof, official identity verification, a fraud finding, or an automatic risk or officer decision.
