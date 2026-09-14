import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrustID — Smart Identity Verification",
  description: "AI-assisted identity and document screening for clearer, evidence-oriented verification decisions.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
