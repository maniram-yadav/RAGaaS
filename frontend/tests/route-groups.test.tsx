/**
 * Smoke test for STORY-007's acceptance criterion: all three route groups
 * render without runtime errors. Per-page content is covered in more detail
 * by tests/app/*.test.tsx.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MarketingHomePage from "../app/(marketing)/page";
import AuthLoginPage from "../app/(auth)/login/page";
import PortalDashboardPage from "../app/(portal)/dashboard/page";

describe("route group placeholder/shell pages", () => {
  it("renders the (marketing) home page", () => {
    render(<MarketingHomePage />);
    expect(
      screen.getByRole("heading", { name: /Retrieval-Augmented Generation, as a Service/i }),
    ).toBeInTheDocument();
  });

  it("renders the (auth) login page", () => {
    render(<AuthLoginPage />);
    expect(screen.getByRole("heading", { name: /Log in/i })).toBeInTheDocument();
  });

  it("renders the (portal) dashboard page", () => {
    render(<PortalDashboardPage />);
    expect(screen.getByRole("heading", { name: /Dashboard/i })).toBeInTheDocument();
  });
});
