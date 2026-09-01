import type { Metadata } from "next"
import { redirect } from "next/navigation"
import { auth } from "@clerk/nextjs/server"
import { sitePath } from "@/lib/site-url"
import { isAdminUserId } from "@/lib/admin/is-admin-user"

export const metadata: Metadata = {
  title: "LLMHive Command Center",
  description: "Enterprise administration console for LLMHive operations, providers, and business metrics.",
  alternates: {
    canonical: sitePath('/admin'),
  },
  robots: {
    index: false,
    follow: false,
  },
}

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const { userId } = await auth()

  if (!userId) {
    redirect("/sign-in?redirect_url=/admin/dashboard")
  }

  if (!isAdminUserId(userId)) {
    redirect("/?admin=denied")
  }

  return (
    <div className="dark min-h-screen">
      {children}
    </div>
  )
}
