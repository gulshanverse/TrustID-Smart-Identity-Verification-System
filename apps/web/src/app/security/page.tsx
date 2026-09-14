import type { Metadata } from "next";
import { SecurityPageContent } from "@/components/marketing";

export const metadata: Metadata = { title: "TrustID Security — Controlled & Auditable Screening", description: "Review TrustID principles for controlled access, safe handling, minimal sensitive logging, and evidence-oriented auditability." };
export default function SecurityPage() { return <SecurityPageContent />; }
