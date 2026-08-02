import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { isAuthenticatedPlaceholder } from "../../lib/portal-auth-guard";

export default function PortalLayout({ children }: { children: ReactNode }) {
  if (!isAuthenticatedPlaceholder()) {
    redirect("/login");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-neutral-200 p-6">
        <p className="text-lg font-semibold text-foreground">RAGaaS</p>
        <nav className="mt-6 space-y-2 text-sm text-neutral-600">
          <div>Dashboard</div>
          <div>Documents</div>
          <div>Chat</div>
          <div>Billing</div>
        </nav>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
