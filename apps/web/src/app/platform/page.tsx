import type { Metadata } from "next";
import { PlatformPageContent } from "@/components/marketing";

export const metadata: Metadata = { title: "TrustID Platform — Smart Identity & Document Screening", description: "Explore TrustID capabilities for AI-assisted document screening, identity signals, tampering analysis, and evidence-oriented review." };
export default function PlatformPage() { return <PlatformPageContent />; }
