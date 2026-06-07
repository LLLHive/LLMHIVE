import { auth } from "@clerk/nextjs/server"
import { redirect } from "next/navigation"

type PageProps = {
  params: Promise<{ id: string }>
}

/** Deep link for shared conversations: /chat/:id → /app?conversation=:id */
export default async function ChatDeepLinkPage({ params }: PageProps) {
  const { id } = await params
  const target = `/app?conversation=${encodeURIComponent(id)}`
  const { userId } = await auth()

  if (!userId) {
    redirect(`/sign-in?redirect_url=${encodeURIComponent(target)}`)
  }

  redirect(target)
}
