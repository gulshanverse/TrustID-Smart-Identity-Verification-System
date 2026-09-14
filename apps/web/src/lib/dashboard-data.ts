export type DemoVerificationStatus = "Verified" | "Review" | "High Risk";
export type DemoRiskLevel = "Low" | "Medium" | "High";
export type DemoRole = "ADMIN" | "OFFICER" | "SUPERVISOR" | "AUDITOR";

export interface DashboardSummary {
  total: number;
  verified: number;
  review: number;
  highRisk: number;
  comparison: string;
}

export interface TrendPoint {
  day: string;
  total: number;
  verified: number;
  review: number;
  highRisk: number;
}

export interface RecentVerification {
  reference: string;
  document: string;
  country: string;
  status: DemoVerificationStatus;
  risk: DemoRiskLevel;
  time: string;
  officer: string;
}

export interface PendingReview {
  reference: string;
  issue: string;
  age: string;
  priority: "Priority" | "Standard";
  route: string;
}

export interface DashboardActivity {
  label: string;
  context: string;
  time: string;
  tone: "success" | "warning" | "info" | "neutral";
}

export interface SystemStatus {
  service: string;
  state: "Operational" | "Configured" | "Not connected" | "Not configured";
  detail: string;
  tone: "success" | "info" | "warning" | "neutral";
}

export interface DashboardDemoData {
  summary: DashboardSummary;
  trend: TrendPoint[];
  riskDistribution: Array<{ label: string; value: number; tone: "success" | "warning" | "danger" }>;
  recentVerifications: RecentVerification[];
  pendingReviews: PendingReview[];
  recentActivity: DashboardActivity[];
  systemStatus: SystemStatus[];
}

export const dashboardDemoData: DashboardDemoData = {
  summary: {
    total: 128,
    verified: 91,
    review: 27,
    highRisk: 10,
    comparison: "+12.4% vs previous demo period",
  },
  trend: [
    { day: "Mon", total: 94, verified: 70, review: 18, highRisk: 6 },
    { day: "Tue", total: 101, verified: 74, review: 20, highRisk: 7 },
    { day: "Wed", total: 116, verified: 84, review: 23, highRisk: 9 },
    { day: "Thu", total: 108, verified: 80, review: 20, highRisk: 8 },
    { day: "Fri", total: 119, verified: 87, review: 23, highRisk: 9 },
    { day: "Sat", total: 122, verified: 89, review: 24, highRisk: 9 },
    { day: "Today", total: 128, verified: 91, review: 27, highRisk: 10 },
  ],
  riskDistribution: [
    { label: "Low Risk", value: 91, tone: "success" },
    { label: "Review", value: 27, tone: "warning" },
    { label: "High Risk", value: 10, tone: "danger" },
  ],
  recentVerifications: [
    { reference: "VER-2026-00128", document: "Passport", country: "Republic of Norvale", status: "Verified", risk: "Low", time: "09:42", officer: "A. Mehta" },
    { reference: "VER-2026-00127", document: "Entry Permit", country: "Federation of Lydora", status: "Review", risk: "Medium", time: "09:36", officer: "S. Rao" },
    { reference: "VER-2026-00126", document: "Visa", country: "Kingdom of Ardin", status: "Verified", risk: "Low", time: "09:18", officer: "A. Mehta" },
    { reference: "VER-2026-00125", document: "National ID", country: "Union of Virelia", status: "High Risk", risk: "High", time: "08:57", officer: "N. Das" },
    { reference: "VER-2026-00124", document: "Driving License", country: "Republic of Estara", status: "Verified", risk: "Low", time: "08:41", officer: "S. Rao" },
  ],
  pendingReviews: [
    { reference: "VER-2026-00127", issue: "Validation discrepancy detected", age: "14 min", priority: "Priority", route: "/console/verify" },
    { reference: "VER-2026-00123", issue: "Document expiry requires review", age: "31 min", priority: "Standard", route: "/console/verifications" },
    { reference: "VER-2026-00119", issue: "Face comparison requires review", age: "46 min", priority: "Priority", route: "/console/cases" },
  ],
  recentActivity: [
    { label: "Demo verification completed", context: "VER-2026-00128 · simulated result", time: "2 min ago", tone: "success" },
    { label: "Review queue updated", context: "3 fictional items awaiting review", time: "14 min ago", tone: "warning" },
    { label: "Demo verification created", context: "VER-2026-00127 · display-only record", time: "31 min ago", tone: "info" },
    { label: "System health check completed", context: "API responded to local readiness check", time: "1 hr ago", tone: "neutral" },
    { label: "Officer session started", context: "Demo Officer · simulated access", time: "2 hrs ago", tone: "info" },
  ],
  systemStatus: [
    { service: "API", state: "Operational", detail: "Health endpoint available", tone: "success" },
    { service: "Database", state: "Configured", detail: "Persistence boundary ready", tone: "info" },
    { service: "Cache", state: "Configured", detail: "Coordination layer reserved", tone: "info" },
    { service: "Object Storage", state: "Configured", detail: "Local artifact boundary reserved", tone: "info" },
    { service: "AI Providers", state: "Not connected", detail: "Provider interfaces only", tone: "warning" },
    { service: "External Government APIs", state: "Not connected", detail: "No external records are queried", tone: "neutral" },
  ],
};

export function percentage(value: number, total = dashboardDemoData.summary.total): string {
  return `${((value / total) * 100).toFixed(1)}%`;
}

export function dashboardDataIsCoherent(data: DashboardDemoData): boolean {
  const { total, verified, review, highRisk } = data.summary;
  return total === verified + review + highRisk
    && data.riskDistribution.reduce((sum, item) => sum + item.value, 0) === total
    && data.trend.every((point) => point.total === point.verified + point.review + point.highRisk);
}

export const DASHBOARD_ROLES: DemoRole[] = ["ADMIN", "OFFICER", "SUPERVISOR", "AUDITOR"];
