import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrustID — Smart Identity Verification",
  description: "Foundation shell for TrustID identity and document screening.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
