import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

export interface TableColumn<Row> {
  key: string;
  header: string;
  render?: (row: Row) => ReactNode;
}

export interface TableProps<Row extends Record<string, unknown>> {
  columns: Array<TableColumn<Row>>;
  rows: Row[];
  emptyState?: ReactNode;
  className?: string;
}

/**
 * Base `components/ui` table primitive with a built-in empty state — the
 * only variant this story needs; row/pagination behavior lands with the
 * features that consume it (documents list, admin config, billing history).
 */
export function Table<Row extends Record<string, unknown>>({
  columns,
  rows,
  emptyState = "No data yet.",
  className,
}: TableProps<Row>) {
  return (
    <table className={cn("w-full border-collapse text-left text-sm", className)}>
      <thead>
        <tr className="border-b border-neutral-200">
          {columns.map((column) => (
            <th key={column.key} className="px-4 py-2 font-medium text-neutral-600">
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr>
            <td
              colSpan={columns.length}
              className="px-4 py-8 text-center text-neutral-500"
            >
              {emptyState}
            </td>
          </tr>
        ) : (
          rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-neutral-100">
              {columns.map((column) => (
                <td key={column.key} className="px-4 py-2 text-foreground">
                  {column.render ? column.render(row) : String(row[column.key] ?? "")}
                </td>
              ))}
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}
