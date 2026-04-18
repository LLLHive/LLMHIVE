import { NextResponse } from "next/server"
import { auth, clerkClient } from "@clerk/nextjs/server"

/**
 * Updates the signed-in user's display name (first/last) in Clerk.
 */
export async function PATCH(req: Request) {
  try {
    const { userId } = await auth()
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = (await req.json()) as { displayName?: string }
    const nameParts = (body.displayName ?? "").trim().split(/\s+/)
    const firstName = nameParts[0] || ""
    const lastName = nameParts.slice(1).join(" ") || ""

    const client = await clerkClient()
    await client.users.updateUser(userId, { firstName, lastName })

    return NextResponse.json({ ok: true })
  } catch (e) {
    console.error("[account-name] PATCH failed:", e)
    return NextResponse.json({ error: "Failed to update name" }, { status: 500 })
  }
}
