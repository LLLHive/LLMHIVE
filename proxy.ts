import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server"
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"
import {
  BUSINESS_OPS_GATE_COOKIE,
  businessOpsGateConfigured,
  isBusinessOpsProtectedPath,
  verifyBusinessOpsGateCookie,
} from "@/lib/business-ops-gate"

// =============================================================================
// Route Configuration
// =============================================================================

/**
 * Public routes that don't require authentication.
 * These routes are accessible to everyone including non-logged-in users.
 */
const isPublicRoute = createRouteMatcher([
  // Public marketing landing — root must be reachable by anonymous traffic.
  "/",

  // Auth routes
  "/sign-in(.*)",
  "/sign-up(.*)",

  // Marketing / SEO pages — every directory under app/(marketing)/* needs to
  // be reachable without auth or visitors get bounced to /sign-in.
  "/landing(.*)",
  "/pricing(.*)",
  "/about(.*)",
  "/terms(.*)",
  "/privacy(.*)",
  "/cookies(.*)",
  "/contact(.*)",
  "/demo(.*)",
  "/help(.*)",
  "/faq(.*)",
  "/press(.*)",
  "/promo(.*)",
  "/comparisons(.*)",
  "/case-studies(.*)",
  "/use-cases(.*)",
  "/industries(.*)",
  "/alternatives(.*)",
  "/best-ai-assistant-for(.*)",
  "/best-for(.*)",

  // SEO-discoverable utility files served by app/.
  "/sitemap.xml",
  "/robots.txt",
  "/llms.txt",

  // API routes that should be public
  "/api/webhooks(.*)",
  "/api/health",
  "/api/openrouter(.*)",  // OpenRouter API routes for model catalog
  "/api/settings(.*)",    // Settings API for loading user preferences

  // Stripe webhook handler (singular + plural URLs both registered in
  // Stripe Dashboard). MUST be public — Stripe authenticates with the
  // signed payload, not a Clerk session. Without this exemption, Clerk
  // intercepts every Stripe POST and returns its sign-in HTML, which is
  // exactly what was producing the 404/405 errors in Stripe's
  // event-deliveries log even though the route file existed.
  "/api/billing/webhook",
  "/api/billing/webhooks",
])

// Check if running in E2E test mode
const isE2ETest = process.env.PLAYWRIGHT_TEST === "true" || process.env.CI === "true"

// =============================================================================
// Clerk Auth Middleware
// =============================================================================

/** True when the request targets an `/api/...` route. */
function isApiRequest(request: NextRequest): boolean {
  return request.nextUrl.pathname.startsWith("/api/")
}

/**
 * Clerk proxy for authentication (Next.js 16+).
 *
 * - Public routes are accessible to everyone.
 * - HTML routes that require auth get redirected to /sign-in via
 *   `auth.protect()` (Clerk's default behaviour).
 * - API routes that require auth get a JSON `401 Unauthorized` instead of
 *   Clerk's default `notFound()` (which renders Next.js's 404 HTML page).
 *   The 404 fallback was surfacing in the chat UI as the opaque
 *   "Request failed: 404" error whenever a session token went stale.
 * - E2E tests bypass authentication.
 */
export const proxy = clerkMiddleware(async (auth, request) => {
  // Skip auth in E2E test mode to allow automated testing.
  if (isE2ETest) {
    return
  }

  if (!isPublicRoute(request)) {
    const { userId } = await auth()

    if (!userId) {
      if (isApiRequest(request)) {
        // Return a real 401 with a JSON body so client-side fetch wrappers
        // (lib/api-client.ts -> parseErrorResponse) can show "Please sign
        // in to continue" instead of "Request failed: 404".
        return NextResponse.json(
          {
            error: "Authentication required. Please sign in to continue.",
            code: "session_required",
          },
          { status: 401 },
        )
      }
      // HTML route — let Clerk handle the sign-in redirect as before.
      await auth.protect()
    }
  }

  const { userId } = await auth()
  const pathname = request.nextUrl.pathname
  if (
    businessOpsGateConfigured() &&
    userId &&
    isBusinessOpsProtectedPath(pathname) &&
    !verifyBusinessOpsGateCookie(request.cookies.get(BUSINESS_OPS_GATE_COOKIE)?.value)
  ) {
    const gate = new URL("/business-ops/gate", request.url)
    gate.searchParams.set("returnTo", pathname + request.nextUrl.search)
    return NextResponse.redirect(gate)
  }
})

export const config = {
  // Match all routes except static files and Next.js internals
  matcher: [
    // Skip Next.js internals and static files
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
}
