import { Suspense } from "react"
import { ChatInterface } from "@/components/chat-interface"
import { Skeleton } from "@/components/loading-skeleton"

// Loading skeleton for the chat interface
function ChatInterfaceLoading() {
  return (
    <div className="flex h-screen w-full overflow-hidden">
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

export default function Home() {
  return (
    <main className="h-screen w-full overflow-hidden">
      <Suspense fallback={<ChatInterfaceLoading />}>
        <ChatInterface />
      </Suspense>
    </main>
  )
}
