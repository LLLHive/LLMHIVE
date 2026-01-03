import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server"

// =============================================================================
// Route Configuration
// =============================================================================

// Define public routes that don't require authentication
const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/webhooks(.*)",
  "/api/health",
  "/api/openrouter(.*)",  // OpenRouter API routes should be public for model catalog
  "/api/settings(.*)",    // Settings API for loading user preferences
])

// Check if running in E2E test mode
const isE2ETest = process.env.PLAYWRIGHT_TEST === "true" || process.env.CI === "true"

// =============================================================================
// Clerk Auth Proxy (renamed from middleware for Next.js 16+)
// =============================================================================

// Named export "proxy" for Next.js 16+ (replaces default export "middleware")
export const proxy = clerkMiddleware(async (auth, request) => {
  // Skip auth in E2E test mode to allow automated testing
  if (isE2ETest) {
    return
  }
  
  // Protect all routes except public ones
  if (!isPublicRoute(request)) {
    await auth.protect()
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
