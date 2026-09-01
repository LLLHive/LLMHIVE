import type { Metadata } from "next"
import { redirect } from "next/navigation"
import { auth } from "@clerk/nextjs/server"
import { sitePath } from "@/lib/site-url"
import { isAdminUserId } from "@/lib/admin/is-admin-user"

export const metadata: Metadata = {
  title: "LLMHive Analytics",
  description: "Monitor performance, feedback, and usage analytics in LLMHive.",
  alternates: {
    canonical: sitePath('/analytics'),
  },
  robots: {
    index: false,
    follow: false,
  },
}

export default async function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  const { userId } = await auth()

  if (!userId) {
    redirect("/sign-in?redirect_url=/analytics")
  }

  if (!isAdminUserId(userId)) {
    redirect("/?admin=denied")
  }

  return <>{children}</>
}
