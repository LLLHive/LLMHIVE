/** LLMHive Meta (Facebook) Pixel ID — public, visible in page source. */
export const META_PIXEL_ID =
  process.env.NEXT_PUBLIC_META_PIXEL_ID?.trim() || "2260132784520343"

/** Load Meta Pixel on production only so local dev does not pollute Event Manager. */
export function isMetaPixelEnabled(): boolean {
  return process.env.NODE_ENV === "production" && META_PIXEL_ID.length > 0
}
