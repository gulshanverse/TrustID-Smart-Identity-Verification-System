import { BarChart3, ClipboardCheck, FileClock, FileText, History, LayoutDashboard, Menu, Search, Settings, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { DemoModeBadge, TrustIDLogo } from "./status";

const publicLinks = [
  ["Platform", "/platform"],
  ["How It Works", "/how-it-works"],
  ["Technology", "/technology"],
  ["Security", "/security"],
  ["About", "/about"],
] as const;

const consoleNav = [{ label: "Dashboard", icon: LayoutDashboard }, { label: "Verification", icon: ClipboardCheck, children: ["New Verification", "History"] }, { label: "Cases", icon: FileText }, { label: "Investigation", icon: Search }, { label: "Analytics", icon: BarChart3 }, { label: "Audit Trail", icon: FileClock }, { label: "Reports", icon: FileText }, { label: "Settings", icon: Settings }];

export function PageContainer({ children }: { children: ReactNode }) { return <div className="page-container">{children}</div>; }
export function ContentContainer({ children }: { children: ReactNode }) { return <div className="content-container">{children}</div>; }

export function PublicHeader() {
  return <header className="public-header">
    <a href="/" aria-label="TrustID home"><TrustIDLogo /></a>
    <nav className="desktop-public-nav" aria-label="Public navigation">{publicLinks.map(([label, href]) => <a href={href} key={href}>{label}</a>)}</nav>
    <div className="header-actions"><a className="sign-in" href="/login">Sign In</a><a className="button button-primary" href="/login">Start Verification</a></div>
    <details className="mobile-navigation"><summary aria-label="Open public navigation"><Menu size={20} /><span>Menu</span></summary><nav aria-label="Mobile public navigation">{publicLinks.map(([label, href]) => <a href={href} key={href}>{label}</a>)}<a href="/login">Sign In</a><a href="/login">Start Verification</a></nav></details>
  </header>;
}

export function PublicFooter() {
  return <footer className="marketing-footer"><div><strong>TrustID</strong><span>Smart Identity Verification</span></div><div className="footer-links"><a href="/platform">Platform</a><a href="/security">Security</a><a href="/technology">Technology</a><a href="/about">About</a></div><small>Demo concept · AI-assisted decision support · Not an official government deployment</small></footer>;
}

export function ConsoleSidebar() { return <aside className="console-sidebar"><div className="sidebar-brand"><TrustIDLogo /></div><div className="sidebar-label">OPERATIONS</div><nav aria-label="Console navigation">{consoleNav.map(({ label, icon: Icon, children }) => <div key={label} className="nav-group"><a href={`#${label.toLowerCase().replaceAll(" ", "-")}`}><Icon size={17} />{label}</a>{children?.map((child) => <a className="nav-child" href={`#${child.toLowerCase().replaceAll(" ", "-")}`} key={child}>{child}</a>)}</div>)}</nav><div className="sidebar-bottom"><DemoModeBadge /><p><ShieldCheck size={14} /> Evidence-first workflow</p></div></aside>; }
export function ConsoleHeader({ title = "Operations console" }: { title?: string }) { return <header className="console-header"><button className="mobile-menu" aria-label="Open navigation"><Menu size={20} /></button><div><span className="header-kicker">TRUSTID CONSOLE</span><h1>{title}</h1></div><div className="console-actions"><button className="icon-button" aria-label="Search"><Search size={18} /></button><button className="icon-button" aria-label="Verification history"><History size={18} /></button><div className="profile-chip"><span>AO</span><div><strong>Authorized Officer</strong><small>Demo environment</small></div></div></div></header>; }
export function ConsoleShell({ children }: { children: ReactNode }) { return <div className="console-shell"><ConsoleSidebar /><div className="console-main"><ConsoleHeader />{children}</div></div>; }
