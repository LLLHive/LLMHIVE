/** LLMHive marketing GTM container (public — visible in page source). */
export const GTM_CONTAINER_ID =
  process.env.NEXT_PUBLIC_GTM_ID?.trim() || "GTM-M7NC48W8"

/** Load GTM on production only so local dev does not pollute agency analytics. */
export function isGtmEnabled(): boolean {
  return process.env.NODE_ENV === "production" && GTM_CONTAINER_ID.length > 0
}
