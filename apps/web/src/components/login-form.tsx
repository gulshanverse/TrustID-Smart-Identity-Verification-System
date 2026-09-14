"use client";

import { Eye, EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { DemoModeBadge } from "./status";

export function LoginForm() {
  const { signIn, loading, error } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setValidationError(null);
    if (!identifier.trim() || !password) { setValidationError("Enter your email or username and password."); return; }
    const success = await signIn(identifier, password);
    if (success) router.replace(searchParams.get("next") ?? "/console/dashboard");
  };

  return <form className="login-form" onSubmit={submit} noValidate>
    <label htmlFor="identifier">Email or username<input id="identifier" name="identifier" autoComplete="username" value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="name@organization.example" /></label>
    <label htmlFor="password">Password<div className="password-input"><input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /><button type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>
    {(validationError || error) && <p className="login-error" role="alert">{validationError ?? error}</p>}
    <button className="button button-primary login-submit" disabled={loading} type="submit">{loading ? "Signing in…" : "Sign in to secure console"}</button>
    <p className="login-security"><LockKeyhole size={14} /> Secure session · HttpOnly cookie · Authorized personnel only</p>
    <div className="demo-login-note"><DemoModeBadge /><p>Development demo accounts are configured through server environment settings. No demo password is embedded in the application.</p></div>
  </form>;
}

export function LoginHeader() { return <div className="login-brand"><span className="brand-mark"><ShieldCheck size={22} /></span><div><strong>TrustID</strong><span>Secure Console</span></div></div>; }
