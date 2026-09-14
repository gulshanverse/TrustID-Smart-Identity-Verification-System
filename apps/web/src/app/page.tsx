export default function HomePage() {
  return (
    <main className="shell">
      <div className="eyebrow">TRUSTID · FOUNDATION</div>
      <h1>Smart Identity Verification</h1>
      <p className="lead">
        Verify. Detect. Protect. The application foundation is ready for the next TrustID phase.
      </p>
      <div className="status-card" role="status">
        <span className="status-mark">✓</span>
        <div>
          <strong>Phase 0 foundation ready</strong>
          <p>Frontend shell, API boundaries, shared contracts, and local infrastructure are configured.</p>
        </div>
      </div>
      <p className="notice">
        This is an engineering foundation only. No verification, AI provider, government integration, or decision workflow is active yet.
      </p>
    </main>
  );
}
