import type { Metadata } from "next";

import { Card } from "../../../components/ui/Card";

export function generateMetadata(): Metadata {
  return {
    title: "Pricing — RAGaaS",
    description: "RAGaaS plans and pricing (placeholder — real plans land in STORY-052).",
    openGraph: {
      title: "Pricing — RAGaaS",
      description: "RAGaaS plans and pricing.",
      type: "website",
    },
  };
}

export default function PricingPage() {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-foreground">Pricing</h1>
        <p className="mt-2 text-neutral-600">
          Plan details are wired to the billing API in a later story — this is a
          placeholder layout.
        </p>
      </div>
      <div className="grid gap-6 sm:grid-cols-3">
        <Card title="Free">
          <p className="text-sm text-neutral-600">Plan details coming soon.</p>
        </Card>
        <Card title="Pro">
          <p className="text-sm text-neutral-600">Plan details coming soon.</p>
        </Card>
        <Card title="Enterprise">
          <p className="text-sm text-neutral-600">Plan details coming soon.</p>
        </Card>
      </div>
    </div>
  );
}
