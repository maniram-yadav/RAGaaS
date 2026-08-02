import Link from "next/link";
import type { ReactNode } from "react";

/**
 * Shared shell for the SEO-facing marketing pages (home/pricing/about).
 * Server Component — no interactivity needed for the nav/footer scaffold.
 */
export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-neutral-200">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-lg font-semibold text-foreground">
            RAGaaS
          </Link>
          <div className="flex gap-6 text-sm text-neutral-600">
            <Link href="/pricing">Pricing</Link>
            <Link href="/about">About</Link>
            <Link href="/login">Log in</Link>
          </div>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-12">{children}</main>
      <footer className="border-t border-neutral-200 px-6 py-6 text-center text-sm text-neutral-500">
        © {new Date().getFullYear()} RAGaaS. All rights reserved.
      </footer>
    </div>
  );
}
