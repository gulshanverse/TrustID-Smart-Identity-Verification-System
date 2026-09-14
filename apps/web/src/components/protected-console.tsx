"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ConsoleShell } from "./layouts";
import { StatePanel } from "./ui";

export function ProtectedConsole({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => { if (!loading && !user) router.replace("/login?next=/console/dashboard"); }, [loading, router, user]);
  if (loading) return <div className="console-loading"><StatePanel state="loading" title="Loading secure console..." description="Checking the current session." /></div>;
  if (!user) return <div className="console-loading"><StatePanel state="warning" title="Authentication required" description="Redirecting to the secure sign-in page." /></div>;
  return <ConsoleShell user={user}>{children}</ConsoleShell>;
}
