# TrustID public website

Phase 2 implements the public TrustID website on top of the Phase 1 design system. The homepage presents the product in the required conceptual order: hero, problem, solution, lifecycle, core capabilities, verification intelligence, security, use cases, technology, CTA, and footer.

## Routes

The public routes are `/`, `/platform`, `/how-it-works`, `/technology`, `/security`, and `/about`. `/login` is a clearly labeled secure-console placeholder; it does not implement authentication or imply that anonymous visitors can perform protected verification.

Every informational page uses the shared public header and footer. The header links to the public routes and routes both `Sign In` and `Start Verification` to the placeholder secure entry point.

## Messaging boundaries

The site consistently describes TrustID as an AI-assisted decision-support platform. It uses evidence-oriented language such as possible tampering indicators, explainable risk assessment, authorized personnel, and authorized external verification sources when integrated. It does not claim government verification, certifications, guaranteed security, perfect fraud detection, or autonomous legal decisions.

## Visual communication

The homepage hero uses a fictional, demo-safe verification preview showing document fields, analysis signals, risk context, and evidence availability. The site uses the existing TrustID navy/blue light theme, semantic status colors, restrained motion, responsive grids, and accessible links with meaningful labels. No real identity data or face imagery is used.

## Scope boundary

Phase 2 remains informational. It does not implement secure authentication, document upload, OCR, validation, tampering detection, face verification, risk calculation, cases, analytics, reports, blockchain, or government APIs.
