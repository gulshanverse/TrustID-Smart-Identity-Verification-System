# TrustID operational dashboard

Phase 4 extends the protected `/console/dashboard` route into a deterministic operational dashboard. It remains a presentation layer only: every metric, trend point, reference, review prompt, activity entry, and system status is fictional display data and is visibly marked as demo or simulated.

## Data architecture

The typed dataset lives in `apps/web/src/lib/dashboard-data.ts` as `DashboardDemoData`. It contains the summary metrics, seven-day trend, risk distribution, recent display records, pending review prompts, demo activity, and architecture-aware service statuses. The dashboard UI consumes this object through small presentation components in `apps/web/src/components/dashboard.tsx`.

The dataset has a coherence helper that verifies that summary outcomes add up to the total, risk categories match the same total, and each trend point is internally consistent. Percentages are derived from the shared total rather than independently hardcoded.

## Production replacement seam

The intended future replacement is a dashboard data provider that reads from an authorized API endpoint:

```text
OperationalDashboard
        ↓
DashboardDataProvider
        ↓
DemoDashboardData now; API response later
        ↓
Verification, case, audit, and service repositories
```

This phase deliberately does not add dashboard persistence, fake verification tables, a dashboard API, document processing, OCR, AI providers, risk calculation, or external integrations.

## Dashboard sections

The protected page includes KPI summary cards, verification activity trend, risk distribution, recent fictional verification records, pending review prompts, dashboard-only activity, system readiness, role context, and quick actions to existing protected routes. Review actions lead only to structural placeholder destinations and are not presented as real investigations.

The existing authenticated console shell, role-aware navigation, cookie sessions, API authorization, and logout behavior are unchanged. The dashboard can adapt its contextual message to the current `ADMIN`, `OFFICER`, `SUPERVISOR`, or `AUDITOR` role without bypassing backend authorization.

## Data-safety boundary

Demo references use synthetic `VER-2026-*` identifiers, fictional country names, fictional officer names, and document-type labels. No passport numbers, government IDs, biometric data, addresses, phone numbers, real identity records, or real operational events are included. System status uses `Operational`, `Configured`, `Not connected`, and `Not configured` states rather than fabricated uptime or provider claims.
