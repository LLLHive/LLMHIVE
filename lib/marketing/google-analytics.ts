/** GA4 measurement ID (public — visible in page source). */
export const GA_MEASUREMENT_ID =
  process.env.NEXT_PUBLIC_GA_ID?.trim() || "G-47VR44WL6N"

/** Load GA on production only so local dev does not pollute analytics. */
export function isGoogleAnalyticsEnabled(): boolean {
  return process.env.NODE_ENV === "production" && GA_MEASUREMENT_ID.length > 0
}
