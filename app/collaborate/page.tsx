"use client"

import { Suspense, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { stashCollaborateSession } from "@/lib/collaborate-deeplink"
import { Loader2 } from "lucide-react"

function CollaborateJoinContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { isAuthenticated, isLoading } = useAuth()
  const session = searchParams.get("session")

  useEffect(() => {
    if (isLoading) return

    if (!session?.trim()) {
      router.replace("/app")
      return
    }

    const sessionId = session.trim()

    if (!isAuthenticated) {
      router.replace(
        `/sign-in?redirect_url=${encodeURIComponent(`/collaborate?session=${encodeURIComponent(sessionId)}`)}`,
      )
      return
    }

    stashCollaborateSession(sessionId)
    router.replace("/app")
  }, [isAuthenticated, isLoading, router, session])

  return (
    <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
      Joining collaboration session…
    </div>
  )
}

export default function CollaborateJoinPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          Loading…
        </div>
      }
    >
      <CollaborateJoinContent />
    </Suspense>
  )
}
