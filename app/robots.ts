import type { MetadataRoute } from "next"
import { getSiteUrl } from "@/lib/site-url"

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
    sitemap: `${getSiteUrl()}/sitemap.xml`,
  }
}
