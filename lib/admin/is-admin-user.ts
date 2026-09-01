/** Clerk user IDs allowed to access admin routes and analytics. */
export function getAdminUserIds(): string[] {
  return process.env.ADMIN_USER_IDS?.split(",").map((id) => id.trim()).filter(Boolean) ?? []
}

/** True only when the user ID is explicitly listed in ADMIN_USER_IDS. */
export function isAdminUserId(userId: string | null | undefined): boolean {
  if (!userId) return false
  const admins = getAdminUserIds()
  return admins.length > 0 && admins.includes(userId)
}

export function isAdminConfigured(): boolean {
  return getAdminUserIds().length > 0
}
