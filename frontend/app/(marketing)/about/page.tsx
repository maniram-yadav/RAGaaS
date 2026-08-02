import type { Metadata } from "next";

export function generateMetadata(): Metadata {
  return {
    title: "About — RAGaaS",
    description:
      "RAGaaS connects private data to LLMs behind a configurable, multi-tenant retrieval-augmented generation backend.",
    openGraph: {
      title: "About — RAGaaS",
      description: "About RAGaaS.",
      type: "website",
    },
  };
}

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-3xl font-bold text-foreground">About RAGaaS</h1>
      <p className="text-neutral-600">
        RAGaaS (Retrieval-Augmented Generation as a Service) connects private data to LLMs:
        ingestion, vector storage, retrieval, and generation behind a configurable,
        multi-tenant backend.
      </p>
    </div>
  );
}
