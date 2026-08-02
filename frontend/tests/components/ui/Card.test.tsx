import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Card } from "../../../components/ui/Card";

describe("Card", () => {
  it("renders a title and children", () => {
    render(
      <Card title="Documents">
        <p>content</p>
      </Card>,
    );
    expect(screen.getByRole("heading", { name: "Documents" })).toBeInTheDocument();
    expect(screen.getByText("content")).toBeInTheDocument();
  });

  it("renders without a title", () => {
    render(<Card>content only</Card>);
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    expect(screen.getByText("content only")).toBeInTheDocument();
  });
});
