"use client";

import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Database,
  FileClock,
  FileText,
  HardDrive,
  Info,
  Layers3,
  ScanLine,
  Server,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import {
  dashboardDemoData,
  percentage,
  type DashboardActivity,
  type DemoRiskLevel,
  type DemoVerificationStatus,
  type SystemStatus,
} from "@/lib/dashboard-data";
import { Badge, Card, CardHeader } from "./ui";
import { DemoModeBadge } from "./status";

const data = dashboardDemoData;

function statusClass(status: DemoVerificationStatus): string {
  return status === "Verified" ? "status-verified" : status === "Review" ? "status-review" : "status-danger";
}

function riskClass(risk: DemoRiskLevel): string {
  return risk === "Low" ? "badge-success" : risk === "Medium" ? "badge-warning" : "badge-danger";
}

function activityIcon(item: DashboardActivity) {
  if (item.tone === "success") return <CheckCircle2 size={16} />;
  if (item.tone === "warning") return <AlertTriangle size={16} />;
  if (item.tone === "info") return <Info size={16} />;
  return <Activity size={16} />;
}

function serviceIcon(service: string) {
  if (service === "API") return <Server size={16} />;
  if (service === "Database") return <Database size={16} />;
  if (service === "Cache") return <Layers3 size={16} />;
  if (service === "Object Storage") return <HardDrive size={16} />;
  return <ShieldCheck size={16} />;
}

function KPIIcon({ kind }: { kind: "total" | "verified" | "review" | "risk" }) {
  if (kind === "total") return <ScanLine size={19} />;
  if (kind === "verified") return <ShieldCheck size={19} />;
  if (kind === "review") return <ClipboardCheck size={19} />;
  return <ShieldAlert size={19} />;
}

function KPI({ label, value, context, kind, tone }: { label: string; value: string; context: string; kind: "total" | "verified" | "review" | "risk"; tone: string }) {
  return <Card className="dashboard-kpi"><div className={`kpi-icon kpi-${tone}`}><KPIIcon kind={kind} /></div><div><span className="kpi-label">{label}</span><strong className="kpi-value">{value}</strong><span className="kpi-context">{context}</span></div></Card>;
}

function VerificationTrend() {
  const width = 760;
  const height = 260;
  const pad = { top: 18, right: 18, bottom: 36, left: 38 };
  const max = 140;
  const x = (index: number) => pad.left + (index * (width - pad.left - pad.right)) / (data.trend.length - 1);
  const y = (value: number) => pad.top + ((max - value) * (height - pad.top - pad.bottom)) / max;
  const points = (key: "total" | "verified" | "review" | "highRisk") => data.trend.map((item, index) => `${x(index)},${y(item[key])}`).join(" ");
  const grid = [0, 35, 70, 105, 140];

  return <Card className="dashboard-chart-card"><CardHeader title="Verification Activity" description="Seven-day screening volume from the deterministic demo dataset." action={<Badge tone="neutral">DEMO DATA</Badge>} /><div className="chart-legend" aria-label="Chart legend"><span className="legend-total"><i />Total screenings</span><span className="legend-verified"><i />Verified</span><span className="legend-review"><i />Review</span><span className="legend-risk"><i />High risk</span></div><div className="trend-chart-wrap"><svg className="trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="trend-title trend-description"><title id="trend-title">Verification activity over the last seven demo days</title><desc id="trend-description">A line chart comparing total screenings, verified, review, and high-risk fictional records.</desc>{grid.map((value) => <g key={value}><line className="chart-grid-line" x1={pad.left} x2={width - pad.right} y1={y(value)} y2={y(value)} /><text className="chart-axis-label" x={pad.left - 9} y={y(value) + 4} textAnchor="end">{value}</text></g>)}<polyline className="chart-line chart-line-total" points={points("total")} /><polyline className="chart-line chart-line-verified" points={points("verified")} /><polyline className="chart-line chart-line-review" points={points("review")} /><polyline className="chart-line chart-line-risk" points={points("highRisk")} />{data.trend.map((item, index) => <g key={item.day}><circle className="chart-dot chart-dot-total" cx={x(index)} cy={y(item.total)} r="4"><title>{`${item.day}: ${item.total} total screenings`}</title></circle><text className="chart-axis-label chart-day-label" x={x(index)} y={height - 12} textAnchor="middle">{item.day}</text></g>)}</svg></div></Card>;
}

function RiskDistribution() {
  const total = data.summary.total;
  return <Card className="dashboard-risk-card"><CardHeader title="Risk Distribution — Demo Data" description="Outcome categories are display-only and do not represent real fraud rates." action={<BarChart3 size={18} aria-label="Risk distribution" />} /><div className="risk-summary"><div className="risk-ring" aria-label={`${total} total fictional screenings`}><strong>{total}</strong><span>demo records</span></div><div className="risk-bars">{data.riskDistribution.map((item) => <div className="risk-bar-row" key={item.label}><div className="risk-bar-label"><span><i className={`risk-dot risk-dot-${item.tone}`} />{item.label}</span><strong>{item.value} <small>{percentage(item.value)}</small></strong></div><div className="risk-track"><span className={`risk-fill risk-fill-${item.tone}`} style={{ width: `${(item.value / total) * 100}%` }} /></div></div>)}</div></div></Card>;
}

function RecentVerifications() {
  return <Card className="dashboard-table-card"><CardHeader title="Recent Verifications" description="Fictional display records · no identity data or real document numbers." action={<a className="text-link" href="/console/verifications">View history <ArrowRight size={14} /></a>} /><div className="table-scroll"><table className="dashboard-table"><caption className="sr-only">Recent fictional verification records</caption><thead><tr><th>Reference</th><th>Document</th><th>Country</th><th>Status</th><th>Risk</th><th>Time</th><th>Officer</th></tr></thead><tbody>{data.recentVerifications.map((item) => <tr key={item.reference}><td><strong>{item.reference}</strong></td><td>{item.document}</td><td>{item.country}</td><td><span className={`status-badge ${statusClass(item.status)}`}>{item.status}</span></td><td><span className={`badge ${riskClass(item.risk)}`}>{item.risk}</span></td><td>{item.time}</td><td>{item.officer}</td></tr>)}</tbody></table></div><p className="table-footnote"><Info size={14} /> Display-only demo records. They are not connected to verification processing.</p></Card>;
}

function PendingReviews() {
  return <Card className="dashboard-list-card"><CardHeader title="Pending Review Queue" description="Synthetic review prompts for future workflow design." action={<Badge tone="warning">{data.pendingReviews.length} pending</Badge>} /><div className="review-list">{data.pendingReviews.map((item) => <div className="review-item" key={item.reference}><div className="review-icon"><AlertTriangle size={16} /></div><div className="review-copy"><strong>{item.issue}</strong><span>{item.reference} · {item.age}</span></div><div className="review-actions"><span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span><a href={item.route} aria-label={`Open demo preview for ${item.reference}`}>Review <ArrowRight size={13} /></a></div></div>)}</div><div className="demo-preview-note"><DemoModeBadge /><span>Review actions open structural demo destinations only.</span></div></Card>;
}

function ActivityFeed() {
  return <Card className="dashboard-list-card"><CardHeader title="Recent Activity" description="Dashboard demo activity · separate from the future production audit system." action={<FileClock size={18} aria-label="Recent activity" />} /><div className="activity-feed">{data.recentActivity.map((item) => <div className="activity-item" key={`${item.label}-${item.time}`}><span className={`activity-icon activity-${item.tone}`}>{activityIcon(item)}</span><div><strong>{item.label}</strong><span>{item.context}</span></div><time>{item.time}</time></div>)}</div></Card>;
}

function SystemStatus() {
  return <Card className="dashboard-status-card"><CardHeader title="System Readiness" description="Architecture-aware status; no uptime claims or fabricated provider health." action={<Badge tone="info">LOCAL DEMO</Badge>} /><div className="service-list">{data.systemStatus.map((item: SystemStatus) => <div className="service-row" key={item.service}><span className={`service-icon service-${item.tone}`}>{serviceIcon(item.service)}</span><div><strong>{item.service}</strong><small>{item.detail}</small></div><span className={`service-state service-state-${item.tone}`}>{item.state}</span></div>)}</div></Card>;
}

function RoleContext() {
  const { user } = useAuth();
  if (!user) return null;
  const role = user.roles[0];
  const copy = role === "OFFICER" ? "Officer view prioritizes screening activity, pending reviews, and quick verification access." : role === "SUPERVISOR" ? "Supervisor view includes broader workload and oversight context." : role === "AUDITOR" ? "Auditor view is read-only and oriented toward operational context." : "Administrator view includes the full configured operational context.";
  return <div className="role-context"><ShieldCheck size={16} /><span><strong>{role} workspace</strong>{copy}</span></div>;
}

export function OperationalDashboard() {
  return <div className="dashboard-page"><RoleContext /><div className="dashboard-demo-strip"><Info size={16} /><span><strong>DEMO ENVIRONMENT</strong> All figures, references, outcomes, and activity below are fictional display data for product demonstration.</span></div><section className="dashboard-kpi-grid" aria-label="Demo screening summary"><KPI label="Today's Screenings" value={String(data.summary.total)} context={data.summary.comparison} kind="total" tone="info" /><KPI label="Verified" value={String(data.summary.verified)} context={`${percentage(data.summary.verified)} of demo screenings`} kind="verified" tone="success" /><KPI label="Needs Review" value={String(data.summary.review)} context={`${percentage(data.summary.review)} of demo screenings`} kind="review" tone="warning" /><KPI label="High Risk" value={String(data.summary.highRisk)} context={`${percentage(data.summary.highRisk)} of demo screenings`} kind="risk" tone="danger" /></section><section className="dashboard-top-grid"><VerificationTrend /><RiskDistribution /></section><section className="dashboard-middle-grid"><RecentVerifications /><PendingReviews /></section><section className="dashboard-bottom-grid"><ActivityFeed /><SystemStatus /></section><section className="dashboard-quick-actions"><div><span className="eyebrow">Next actions</span><h3>Continue with a protected workflow</h3><p>The operational shell is ready for future verification processing without inventing live records.</p></div><div className="quick-action-links"><a className="button button-primary" href="/console/verify"><ScanLine size={16} /> New Verification</a><a className="button button-secondary" href="/console/verifications"><FileText size={16} /> View History</a><a className="button button-secondary" href="/console/cases"><FileClock size={16} /> View Cases</a><a className="button button-secondary" href="/console/analytics"><TrendingUp size={16} /> View Analytics</a></div></section></div>;
}
