import type { Metadata } from "next";
import { HowItWorksPageContent } from "@/components/marketing";

export const metadata: Metadata = { title: "How TrustID Works — Evidence-Oriented Identity Screening", description: "Learn how TrustID organizes document analysis, validation, tampering signals, available identity inputs, evidence, and officer decisions." };
export default function HowItWorksPage() { return <HowItWorksPageContent />; }
