/**
 * Singular alias for the Stripe webhook handler.
 *
 * Stripe Dashboard had a destination configured at
 *   https://llmhive.ai/api/billing/webhook   (singular)
 * but the actual route lived at
 *   app/api/billing/webhooks/route.ts        (plural)
 *
 * Every retry from that destination came back as 404 / 405 in the Stripe
 * event-deliveries log, so the Firestore subscription write never happened
 * for users who paid through that destination. Re-export the handler here
 * so both URLs work; we'll keep this in place even after the Dashboard URL
 * is corrected so any past-configured destinations don't break again.
 *
 * Note: route-segment config (`dynamic`, etc.) cannot be re-exported in
 * Next.js, so we re-declare it locally to match the plural route.
 */
export { POST } from "../webhooks/route"

export const dynamic = "force-dynamic"
