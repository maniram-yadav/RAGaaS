import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage, { generateMetadata as homeMetadata } from "../../app/(marketing)/page";
import PricingPage, {
  generateMetadata as pricingMetadata,
} from "../../app/(marketing)/pricing/page";
import AboutPage, { generateMetadata as aboutMetadata } from "../../app/(marketing)/about/page";
import MarketingLayout from "../../app/(marketing)/layout";

describe("(marketing) route group", () => {
  it("renders the home page with links to pricing/about/login", () => {
    render(<HomePage />);
    expect(
      screen.getByRole("heading", { name: /Retrieval-Augmented Generation, as a Service/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /See pricing/i })).toHaveAttribute(
      "href",
      "/pricing",
    );
  });

  it("home page generateMetadata returns a title and description", () => {
    const metadata = homeMetadata();
    expect(metadata.title).toMatch(/RAGaaS/i);
    expect(metadata.description).toBeTruthy();
  });

  it("renders the pricing page", () => {
    render(<PricingPage />);
    expect(screen.getByRole("heading", { name: /^Pricing$/i })).toBeInTheDocument();
  });

  it("pricing page generateMetadata returns a title", () => {
    const metadata = pricingMetadata();
    expect(metadata.title).toMatch(/Pricing/i);
  });

  it("renders the about page", () => {
    render(<AboutPage />);
    expect(screen.getByRole("heading", { name: /About RAGaaS/i })).toBeInTheDocument();
  });

  it("about page generateMetadata returns a title", () => {
    const metadata = aboutMetadata();
    expect(metadata.title).toMatch(/About/i);
  });

  it("renders the shared marketing layout around its children", () => {
    render(
      <MarketingLayout>
        <p>child content</p>
      </MarketingLayout>,
    );
    expect(screen.getByText("child content")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "RAGaaS" })).toHaveAttribute("href", "/");
  });
});
