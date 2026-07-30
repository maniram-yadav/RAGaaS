/**
 * Proves STORY-001's acceptance criterion: `frontend/` serves a placeholder
 * page per route group ((marketing), (auth), (portal)).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MarketingPlaceholderPage from "../app/(marketing)/page";
import AuthPlaceholderPage from "../app/(auth)/login/page";
import PortalPlaceholderPage from "../app/(portal)/dashboard/page";

describe("route group placeholder pages", () => {
  it("renders the (marketing) placeholder", () => {
    render(<MarketingPlaceholderPage />);
    expect(screen.getByText(/RAGaaS — Marketing/i)).toBeInTheDocument();
  });

  it("renders the (auth) placeholder", () => {
    render(<AuthPlaceholderPage />);
    expect(screen.getByText(/RAGaaS — Auth/i)).toBeInTheDocument();
  });

  it("renders the (portal) placeholder", () => {
    render(<PortalPlaceholderPage />);
    expect(screen.getByText(/RAGaaS — Portal/i)).toBeInTheDocument();
  });
});
