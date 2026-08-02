import type { MetadataRoute } from "next";

/**
 * Generates `/robots.txt`. Disallows the authenticated (portal) surface and
 * points crawlers at `/sitemap.xml` for the public (marketing) pages.
 */
export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/api/"],
    },
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
