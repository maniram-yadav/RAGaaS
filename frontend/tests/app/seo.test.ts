import { describe, expect, it } from "vitest";

import sitemap from "../../app/sitemap";
import robots from "../../app/robots";

describe("SEO metadata routes", () => {
  it("sitemap lists the public marketing pages with absolute URLs", () => {
    const entries = sitemap();
    const urls = entries.map((entry) => entry.url);

    expect(urls).toContain("http://localhost:3000");
    expect(urls).toContain("http://localhost:3000/pricing");
    expect(urls).toContain("http://localhost:3000/about");
    for (const entry of entries) {
      expect(entry.url).toMatch(/^https?:\/\//);
    }
  });

  it("robots allows public pages, disallows the portal, and points at the sitemap", () => {
    const result = robots();

    expect(result.rules).toMatchObject({ userAgent: "*", allow: "/" });
    const disallow = Array.isArray(result.rules)
      ? result.rules.flatMap((rule) => rule.disallow ?? [])
      : (result.rules?.disallow ?? []);
    expect(disallow).toContain("/dashboard");
    expect(result.sitemap).toBe("http://localhost:3000/sitemap.xml");
  });
});
