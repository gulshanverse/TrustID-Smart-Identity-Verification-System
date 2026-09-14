"use client";

import { BarChart3, ClipboardCheck, FileClock, FileText, History, LayoutDashboard, Menu, Search, Settings, ShieldCheck, LogOut } from "lucide-react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { DemoModeBadge, TrustIDLogo } from "./status";
import { useAuth, type AuthUser, type Role } from "@/lib/auth";

const publicLinks = [["Platform", "/platform"], ["How It Works", "/how-it-works"], ["Technology", "/technology"], ["Security", "/security"], ["About", "/about"]] as const;
const consoleNav = [
  { label: "Dashboard", href: "/console/dashboard", icon: LayoutDashboard, roles: ["ADMIN", "OFFICER", "SUPERVISOR", "AUDITOR"] },
  { label: "Verification", href: "/console/verify", icon: ClipboardCheck, roles: ["ADMIN", "OFFICER", "SUPERVISOR"] , children: [["New Verification", "/console/verify"], ["History", "/console/verifications"]]},
  { label: "Cases", href: "/console/cases", icon: FileText, roles: ["ADMIN", "OFFICER", "SUPERVISOR"] },
  { label: "Investigation", href: "/console/investigation", icon: Search, roles: ["ADMIN", "OFFICER", "SUPERVISOR"] },
  { label: "Analytics", href: "/console/analytics", icon: BarChart3, roles: ["ADMIN", "SUPERVISOR"] },
  { label: "Audit Trail", href: "/console/audit", icon: FileClock, roles: ["ADMIN", "SUPERVISOR", "AUDITOR"] },
  { label: "Reports", href: "/console/reports", icon: FileText, roles: ["ADMIN", "OFFICER", "SUPERVISOR", "AUDITOR"] },
  { label: "Settings", href: "/console/settings", icon: Settings, roles: ["ADMIN"] },
] satisfies Array<{ label: string; href: string; icon: typeof LayoutDashboard; roles: Role[]; children?: string[][] }>;

export function PageContainer({ children }: { children: ReactNode }) { return <div className="page-container">{children}</div>; }
export function ContentContainer({ children }: { children: ReactNode }) { return <div className="content-container">{children}</div>; }
export function PublicHeader() { return <header className="public-header"><a href="/" aria-label="TrustID home"><TrustIDLogo /></a><nav className="desktop-public-nav" aria-label="Public navigation">{publicLinks.map(([label, href]) => <a href={href} key={href}>{label}</a>)}</nav><div className="header-actions"><a className="sign-in" href="/login">Sign In</a><a className="button button-primary" href="/login">Start Verification</a></div><details className="mobile-navigation"><summary aria-label="Open public navigation"><Menu size={20} /><span>Menu</span></summary><nav aria-label="Mobile public navigation">{publicLinks.map(([label, href]) => <a href={href} key={href}>{label}</a>)}<a href="/login">Sign In</a><a href="/login">Start Verification</a></nav></details></header>; }
export function PublicFooter() { return <footer className="marketing-footer"><div><strong>TrustID</strong><span>Smart Identity Verification</span></div><div className="footer-links"><a href="/platform">Platform</a><a href="/security">Security</a><a href="/technology">Technology</a><a href="/about">About</a></div><small>Demo concept · AI-assisted decision support · Not an official government deployment</small></footer>; }

export function ConsoleSidebar({ user }: { user: AuthUser }) { return <aside className="console-sidebar"><div className="sidebar-brand"><TrustIDLogo /></div><div className="sidebar-label">OPERATIONS</div><nav aria-label="Console navigation">{consoleNav.filter((item) => item.roles.some((role) => user.roles.includes(role))).map(({ label, href, icon: Icon, children }) => <div key={label} className="nav-group"><a href={href}><Icon size={17} />{label}</a>{children?.map(([child, childHref]) => <a className="nav-child" href={childHref} key={child}>{child}</a>)}</div>)}</nav><div className="sidebar-bottom"><DemoModeBadge /><p><ShieldCheck size={14} /> Evidence-first workflow</p><small className="sidebar-role">{user.roles.join(" · ")} · SIMULATED USER</small></div></aside>; }

export function ConsoleHeader({ title = "Operations console", user }: { title?: string; user: AuthUser }) {
  const router = useRouter();
  const { signOut } = useAuth();
  const logout = async () => { await signOut(); router.replace("/login"); };
  return <header className="console-header"><button className="mobile-menu" aria-label="Open console navigation"><Menu size={20} /></button><div><span className="header-kicker">TRUSTID CONSOLE</span><h1>{title}</h1></div><div className="console-actions"><button className="icon-button" aria-label="Search foundation"><Search size={18} /></button><button className="icon-button" aria-label="Verification history"><History size={18} /></button><details className="profile-menu"><summary className="profile-chip"><span>{user.display_name.split(" ").map((part) => part[0]).join("").slice(0, 2)}</span><div><strong>{user.display_name}</strong><small>{user.roles[0]} · Demo mode</small></div></summary><div className="profile-dropdown"><strong>{user.display_name}</strong><span>{user.email}</span><a href="/console/settings">Account settings</a><button onClick={() => void logout}><LogOut size={14} /> Sign out</button></div></details></div></header>;
}
export function ConsoleShell({ children, user, title }: { children: ReactNode; user: AuthUser; title?: string }) { return <div className="console-shell"><ConsoleSidebar user={user} /><div className="console-main"><ConsoleHeader title={title} user={user} />{children}</div></div>; }
