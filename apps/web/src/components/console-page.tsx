import type { ReactNode } from "react";
import { ArrowRight, LockKeyhole } from "lucide-react";
import { Card, SectionHeader, StatePanel } from "./ui";
import { DemoModeBadge } from "./status";
import { ProtectedConsole } from "./protected-console";

export function ConsolePage({ title, description, children, action }: { title: string; description: string; children?: ReactNode; action?: ReactNode }) {
  return <ProtectedConsole><div className="console-content"><div className="console-page-heading"><SectionHeader eyebrow="Secure console" title={title} description={description} />{action}</div>{children}</div></ProtectedConsole>;
}

export function ConsolePlaceholder({ title, description, message }: { title: string; description: string; message: string }) {
  return <ConsolePage title={title} description={description}><Card><StatePanel state="empty" title={message} description="This protected destination is reserved for a future TrustID phase. No records or results are being fabricated." action={<span className="placeholder-note"><DemoModeBadge /> <LockKeyhole size={14} /> Authorized access required</span>} /></Card></ConsolePage>;
}

export function ConsoleActionLink({ href, children }: { href: string; children: ReactNode }) { return <a className="button button-primary" href={href}>{children}<ArrowRight size={16} /></a>; }
