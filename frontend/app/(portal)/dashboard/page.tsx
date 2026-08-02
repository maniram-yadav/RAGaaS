import { Card } from "../../../components/ui/Card";
import { Table } from "../../../components/ui/Table";

interface DocumentRow extends Record<string, unknown> {
  name: string;
  status: string;
  uploadedAt: string;
}

/**
 * Dashboard shell. Real document/usage data is wired in later ingestion
 * stories — this story only owns the layout and empty states.
 */
export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Welcome to RAGaaS. Document and usage data will appear here once ingestion is
          wired up.
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-3">
        <Card title="Documents">
          <p className="text-2xl font-semibold text-foreground">0</p>
        </Card>
        <Card title="Conversations">
          <p className="text-2xl font-semibold text-foreground">0</p>
        </Card>
        <Card title="Plan">
          <p className="text-2xl font-semibold text-foreground">—</p>
        </Card>
      </div>

      <Card title="Recent documents">
        <Table<DocumentRow>
          columns={[
            { key: "name", header: "Name" },
            { key: "status", header: "Status" },
            { key: "uploadedAt", header: "Uploaded" },
          ]}
          rows={[]}
          emptyState="No documents uploaded yet."
        />
      </Card>
    </div>
  );
}
