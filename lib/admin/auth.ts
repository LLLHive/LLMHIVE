import { auth } from "@clerk/nextjs/server"
import { isAdminUserId, isAdminConfigured } from "@/lib/admin/is-admin-user"

export { isAdminConfigured, isAdminUserId, getAdminUserIds } from "@/lib/admin/is-admin-user"

export async function requireAdmin(): Promise<{ userId: string } | { error: Response }> {
  const { userId } = await auth()

  if (!userId) {
    return {
      error: new Response(JSON.stringify({ error: "Unauthorized - Admin access required" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    }
  }

  if (!isAdminUserId(userId)) {
    return {
      error: new Response(JSON.stringify({ error: "Forbidden - Admin access required" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    }
  }

  return { userId }
}
