import Link from "next/link";
import type { ReactNode } from "react";

/**
 * Shared shell for the (auth) route group. Server Component — the actual
 * forms/API wiring land in STORY-024; this story only owns the page shells.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-6">
      <div className="w-full max-w-sm space-y-6">
        <Link href="/" className="block text-center text-lg font-semibold text-foreground">
          RAGaaS
        </Link>
        {children}
      </div>
    </div>
  );
}
