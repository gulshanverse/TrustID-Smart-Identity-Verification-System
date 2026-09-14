# TrustID Smart Identity Verification System

TrustID is an AI-assisted identity and document screening platform for the Smart India Hackathon problem statement 26188: **AI-Based Fake Identity & Document Screening System**.

## Project source of truth

Use both master documents together for all TrustID product, UX, architecture, and implementation work:

- [`TRUSTID_MASTER_SPEC.md`](./TRUSTID_MASTER_SPEC.md) — product and engineering specification, requirements, workflows, routes, data models, safety boundaries, and acceptance criteria.
- [`MANUS_MASTER_CONTEXT_PROMPT.md`](./MANUS_MASTER_CONTEXT_PROMPT.md) — implementation context and operating instructions covering design direction, architecture, demo scenarios, risk semantics, frontend/backend expectations, and delivery standards.

The master specification defines **what TrustID must be**. The master context prompt defines **how TrustID should be designed and implemented**. When extending the project, preserve both documents' requirements, especially the evidence-first decision-support model and the distinction between AI recommendations and authorized officer decisions.

## Product principles

- **Verify. Detect. Protect.**
- Hide technical complexity, but never hide evidence.
- Treat TrustID as decision support, not an automatic legal or criminality determination.
- Keep demo data and simulated integrations clearly labeled.
- Preserve explicit distinctions between processing status, document status, identity result, and risk level.
