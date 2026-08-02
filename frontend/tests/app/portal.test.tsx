import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DashboardPage from "../../app/(portal)/dashboard/page";
import PortalLayout from "../../app/(portal)/layout";
import { isAuthenticatedPlaceholder } from "../../lib/portal-auth-guard";

describe("(portal) route group", () => {
  it("renders the dashboard shell with empty-state stat cards and document table", () => {
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByText(/No documents uploaded yet\./i)).toBeInTheDocument();
  });

  it("placeholder auth guard currently always allows access", () => {
    // Documents the current STORY-007 stub behavior; STORY-024 replaces this
    // with a real session check and must update/replace this assertion.
    expect(isAuthenticatedPlaceholder()).toBe(true);
  });

  it("renders the portal layout (nav + children) when the placeholder guard allows access", () => {
    render(
      <PortalLayout>
        <p>portal child content</p>
      </PortalLayout>,
    );
    expect(screen.getByText("portal child content")).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });
});
