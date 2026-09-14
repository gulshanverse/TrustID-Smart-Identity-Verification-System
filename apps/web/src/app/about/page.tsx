import type { Metadata } from "next";
import { AboutPageContent } from "@/components/marketing";

export const metadata: Metadata = { title: "About TrustID — Smart Identity Verification", description: "Learn about TrustID, an AI-assisted identity and document screening concept for clearer, evidence-oriented decisions." };
export default function AboutPage() { return <AboutPageContent />; }
