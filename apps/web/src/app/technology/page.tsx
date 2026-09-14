import type { Metadata } from "next";
import { TechnologyPageContent } from "@/components/marketing";

export const metadata: Metadata = { title: "TrustID Technology — Modular Verification Architecture", description: "See the modular TrustID architecture connecting public web, verification APIs, service abstractions, and data infrastructure." };
export default function TechnologyPage() { return <TechnologyPageContent />; }
