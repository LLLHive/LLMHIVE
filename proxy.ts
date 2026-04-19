import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server"
import { NextResponse } from "next/server"
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
  // Auth routes
  "/sign-in(.*)",
  "/sign-up(.*)",
  
  // Marketing/public pages (must be accessible for SEO and conversions)
  "/landing(.*)",
  "/pricing(.*)",
  "/about(.*)",
  "/terms(.*)",
  "/privacy(.*)",
  "/cookies(.*)",
  "/contact(.*)",
  "/demo(.*)",
  "/help(.*)",
  
  // API routes that should be public
  "/api/webhooks(.*)",
  "/api/health",
  "/api/openrouter(.*)",  // OpenRouter API routes for model catalog
  "/api/settings(.*)",    // Settings API for loading user preferences
])

// Check if running in E2E test mode
const isE2ETest = process.env.PLAYWRIGHT_TEST === "true" || process.env.CI === "true"

// =============================================================================
// Clerk Auth Middleware
// =============================================================================

/**
 * Clerk proxy for authentication (Next.js 16+).
 * 
 * - Public routes are accessible to everyone
 * - All other routes require authentication
 * - E2E tests bypass authentication
 */
export const proxy = clerkMiddleware(async (auth, request) => {
  // Skip auth in E2E test mode to allow automated testing
  if (isE2ETest) {
    return
  }

  // Protect all routes except public ones
  if (!isPublicRoute(request)) {
    await auth.protect()
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
