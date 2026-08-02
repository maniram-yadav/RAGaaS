import type { Metadata } from "next";
import Link from "next/link";

import { Card } from "../../components/ui/Card";

export function generateMetadata(): Metadata {
  return {
    title: "RAGaaS — Retrieval-Augmented Generation as a Service",
    description:
      "Connect your private data to LLMs with a configurable, multi-tenant RAG backend: ingestion, retrieval, and generation as a service.",
    openGraph: {
      title: "RAGaaS — Retrieval-Augmented Generation as a Service",
      description:
        "Connect your private data to LLMs with a configurable, multi-tenant RAG backend.",
      type: "website",
    },
  };
}

export default function HomePage() {
  return (
    <div className="space-y-12">
      <section className="space-y-4 text-center">
        <h1 className="text-4xl font-bold text-foreground">
          Retrieval-Augmented Generation, as a Service
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-neutral-600">
          Ingest your documents, connect them to an LLM, and get grounded answers with
          citations — behind a configurable, multi-tenant backend.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            href="/signup"
            className="inline-flex items-center justify-center rounded-md bg-brand-600 px-4 py-2 text-base font-medium text-white transition-colors hover:bg-brand-700"
          >
            Get started
          </Link>
          <Link
            href="/pricing"
            className="inline-flex items-center justify-center rounded-md bg-neutral-100 px-4 py-2 text-base font-medium text-neutral-900 transition-colors hover:bg-neutral-200"
          >
            See pricing
          </Link>
        </div>
      </section>

      <section className="grid gap-6 sm:grid-cols-3">
        <Card title="Ingest">
          <p className="text-sm text-neutral-600">
            Upload documents, spreadsheets, and CSVs — chunked and embedded automatically.
          </p>
        </Card>
        <Card title="Retrieve">
          <p className="text-sm text-neutral-600">
            Semantic search over your data with pluggable vector stores and retrieval
            strategies.
          </p>
        </Card>
        <Card title="Generate">
          <p className="text-sm text-neutral-600">
            Grounded, cited Markdown answers from your choice of LLM provider.
          </p>
        </Card>
      </section>
    </div>
  );
}
