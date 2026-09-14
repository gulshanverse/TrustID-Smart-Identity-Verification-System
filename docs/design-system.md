# TrustID design system

Phase 1 establishes a light, institutional visual language for TrustID. The design system uses white and very light neutral surfaces, deep navy and blue brand colors, restrained borders and shadows, moderate corner radii, and Inter typography. The secure console is operational rather than promotional, while public navigation remains clear and responsive.

## Status semantics

TrustID keeps processing state, document status, face result, tampering status, and risk level separate. Components use explicit labels such as `✓ VERIFIED`, `VALID`, `TAMPERING CLEAR`, `LOW RISK`, and `ADDITIONAL REVIEW`; color is never the sole communication channel.

## Component layers

`src/components/ui.tsx` contains composable primitives such as buttons, cards, badges, section headers, state panels, dividers, and progress indicators. `status.tsx` contains TrustID presentation components for verification, processing, document, face, tampering, risk, confidence, evidence, and officer-decision language. `documents.tsx` and `evidence.tsx` provide future-workflow presentation structures without upload or computer-vision logic. `layouts.tsx` provides public header/footer and secure console shell foundations with responsive navigation.

## Interaction and accessibility

Interactive elements use semantic HTML, meaningful labels, visible focus rings, restrained hover transitions, and readable contrast. Loading, empty, warning, error, and success patterns provide explanatory text rather than relying on color or iconography alone. The console navigation is desktop-first and collapses at mobile widths; public navigation remains usable on smaller screens.

## Scope boundary

Phase 1 does not implement authentication, dashboard behavior, document upload, OCR, validation, tampering detection, face verification, risk calculation, cases, analytics, reports, blockchain, or government APIs. Components are presentation foundations that later phases can connect to typed analysis results.
