import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "quiet" | "danger" }) {
  return <button className={`button button-${variant} ${className}`} {...props} />;
}

export function Card({ className = "", children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <section className={`card ${className}`} {...props}>{children}</section>;
}

export function CardHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <header className="card-header"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</header>;
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "info" | "success" | "warning" | "danger"; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Divider() { return <hr className="divider" />; }

export function SectionHeader({ eyebrow, title, description }: { eyebrow?: string; title: string; description?: string }) {
  return <div className="section-header">{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2>{description && <p>{description}</p>}</div>;
}

export function StatePanel({ state, title, description, action }: { state: "loading" | "empty" | "error" | "warning" | "success"; title: string; description: string; action?: ReactNode }) {
  return <div className={`state-panel state-${state}`} role={state === "error" ? "alert" : "status"}><div className="state-icon" aria-hidden="true">{state === "loading" ? "…" : state === "success" ? "✓" : state === "warning" ? "!" : state === "error" ? "×" : "—"}</div><div><strong>{title}</strong><p>{description}</p>{action}</div></div>;
}

export function Progress({ value, label }: { value: number; label: string }) {
  return <div className="progress-wrap"><div className="progress-label"><span>{label}</span><span>{value}%</span></div><div className="progress-track"><div className="progress-value" style={{ width: `${value}%` }} /></div></div>;
}
