import { describe, expect, it } from "vitest";
import { dashboardDataIsCoherent, dashboardDemoData, percentage } from "@/lib/dashboard-data";

describe("operational dashboard demo data", () => {
  it("keeps summary, risk distribution, and trend totals coherent", () => {
    expect(dashboardDataIsCoherent(dashboardDemoData)).toBe(true);
    expect(dashboardDemoData.summary.total).toBe(128);
    expect(dashboardDemoData.riskDistribution.map((item) => item.value)).toEqual([91, 27, 10]);
  });

  it("derives percentages from the shared total", () => {
    expect(percentage(dashboardDemoData.summary.verified)).toBe("71.1%");
    expect(percentage(dashboardDemoData.summary.review)).toBe("21.1%");
    expect(percentage(dashboardDemoData.summary.highRisk)).toBe("7.8%");
  });

  it("uses fictional, display-only references and real routes for actions", () => {
    expect(dashboardDemoData.recentVerifications.every((item) => item.reference.startsWith("VER-2026-"))).toBe(true);
    expect(dashboardDemoData.pendingReviews.every((item) => item.route.startsWith("/console/"))).toBe(true);
    expect(dashboardDemoData.recentVerifications.some((item) => item.document === "Passport")).toBe(true);
  });
});
