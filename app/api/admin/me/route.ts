import { NextResponse } from "next/server"
import { auth } from "@clerk/nextjs/server"
import { isAdminConfigured, isAdminUserId } from "@/lib/admin/is-admin-user"

/**
 * Returns the signed-in user's Clerk ID and admin status.
 * Use this during first-time setup to populate ADMIN_USER_IDS.
 * Does NOT require admin access — any authenticated user may call it.
 */
export async function GET() {
  const { userId } = await auth()

  if (!userId) {
    return NextResponse.json(
      { error: "Not signed in", signedIn: false },
      { status: 401 }
    )
  }

  const adminConfigured = isAdminConfigured()
  const isAdmin = isAdminUserId(userId)

  return NextResponse.json({
    signedIn: true,
    userId,
    isAdmin,
    adminConfigured,
    hint: !adminConfigured
      ? "Set ADMIN_USER_IDS in environment variables to your Clerk user ID, then redeploy."
      : !isAdmin
        ? `Add ${userId} to ADMIN_USER_IDS, then redeploy.`
        : "You have admin access.",
  })
}
