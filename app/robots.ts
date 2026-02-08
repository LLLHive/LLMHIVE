import type { MetadataRoute } from "next"

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/admin",
          "/analytics",
          "/billing",
          "/business-ops",
          "/campaigns",
          "/org",
          "/preferences",
          "/settings",
          "/support",
          "/usage",
          "/utm",
          "/api",
          "/auth",
        ],
      },
    ],
    sitemap: "https://www.llmhive.ai/sitemap.xml",
  }
}
