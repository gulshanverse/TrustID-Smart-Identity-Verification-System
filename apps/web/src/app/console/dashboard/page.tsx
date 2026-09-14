import { OperationalDashboard } from "@/components/dashboard";
import { ConsoleActionLink, ConsolePage } from "@/components/console-page";

export default function DashboardPage() {
  return <ConsolePage title="Operations Dashboard" description="Monitor screening activity, review workload, verification outcomes, and system readiness." action={<ConsoleActionLink href="/console/verify">New Verification</ConsoleActionLink>}><OperationalDashboard /></ConsolePage>;
}
