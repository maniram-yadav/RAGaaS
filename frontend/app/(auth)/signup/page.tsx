import type { Metadata } from "next";
import Link from "next/link";

import { Card } from "../../../components/ui/Card";

export function generateMetadata(): Metadata {
  return {
    title: "Sign up — RAGaaS",
    description: "Create a RAGaaS account.",
    robots: { index: false, follow: false },
  };
}

/**
 * Page shell only — no submit handler/API call yet. Wired to the real auth
 * API in STORY-024.
 */
export default function SignupPage() {
  return (
    <Card title="Sign up">
      <form className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="name" className="text-sm font-medium text-neutral-700">
            Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            autoComplete="name"
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="email" className="text-sm font-medium text-neutral-700">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium text-neutral-700">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Sign up
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-neutral-600">
        Already have an account?{" "}
        <Link href="/login" className="text-brand-600">
          Log in
        </Link>
      </p>
    </Card>
  );
}
