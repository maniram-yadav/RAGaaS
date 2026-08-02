import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Table } from "../../../components/ui/Table";

interface Row extends Record<string, unknown> {
  name: string;
  status: string;
}

describe("Table", () => {
  it("renders the empty state when there are no rows", () => {
    render(
      <Table<Row>
        columns={[
          { key: "name", header: "Name" },
          { key: "status", header: "Status" },
        ]}
        rows={[]}
        emptyState="Nothing here yet."
      />,
    );
    expect(screen.getByText("Nothing here yet.")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders rows using the default cell renderer", () => {
    render(
      <Table<Row>
        columns={[
          { key: "name", header: "Name" },
          { key: "status", header: "Status" },
        ]}
        rows={[{ name: "report.pdf", status: "indexed" }]}
      />,
    );
    expect(screen.getByText("report.pdf")).toBeInTheDocument();
    expect(screen.getByText("indexed")).toBeInTheDocument();
    expect(screen.queryByText("Nothing here yet.")).not.toBeInTheDocument();
  });

  it("uses a custom render function when provided", () => {
    render(
      <Table<Row>
        columns={[
          { key: "name", header: "Name" },
          {
            key: "status",
            header: "Status",
            render: (row) => `[${row.status}]`,
          },
        ]}
        rows={[{ name: "report.pdf", status: "indexed" }]}
      />,
    );
    expect(screen.getByText("[indexed]")).toBeInTheDocument();
  });
});
