/**
 * True when running `next dev` with Clerk *production* publishable keys.
 * Clerk rejects localhost for pk_live_, so <SignIn /> / <SignUp /> render nothing.
 */
export function isProductionClerkKeyOnLocalDev(): boolean {
  if (process.env.NODE_ENV !== "development") return false
  const pk = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim() ?? ""
  return pk.startsWith("pk_live_")
}
