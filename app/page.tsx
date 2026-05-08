import { Suspense } from "react"
import { auth } from "@clerk/nextjs/server"
import { redirect } from "next/navigation"
import { ChatInterface } from "@/components/chat-interface"
import { Skeleton } from "@/components/loading-skeleton"
import { OnboardingWrapper } from "@/components/onboarding-wrapper"
import { getPaidEntitlement, paidAccessRedirectUrl } from "@/lib/billing/entitlement"

// Loading skeleton for the chat interface
function ChatInterfaceLoading() {
  return (
    <div className="flex h-[100dvh] max-h-[100dvh] w-full overflow-hidden">
      <div className="w-64 h-full bg-card/50 animate-pulse" />
      <div className="flex-1 flex flex-col">
        <div className="h-16 bg-card/50 animate-pulse border-b" />
        <div className="flex-1 p-4">
          <div className="max-w-4xl mx-auto space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-3/4" />
          </div>
        </div>
      </div>
    </div>
  )
}

export default async function Home() {
  const { userId } = await auth()
  if (!userId) {
    redirect("/sign-in")
  }

  const entitlement = await getPaidEntitlement(userId)
  if (!entitlement.hasPaidAccess) {
    redirect(paidAccessRedirectUrl(entitlement.status))
  }

  return (
    <main className="flex h-[100dvh] max-h-[100dvh] min-h-0 w-full flex-col overflow-hidden overscroll-none">
      <Suspense fallback={<ChatInterfaceLoading />}>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <ChatInterface />
        </div>
      </Suspense>
      {/* Onboarding modal for first-time users */}
      <OnboardingWrapper />
    </main>
  )
}
