import { Suspense } from "react"
import type { Metadata } from "next"
import { BusinessOpsGateForm } from "./gate-form"

export const metadata: Metadata = {
  title: "Business Ops access",
  robots: { index: false, follow: false },
}

export default function BusinessOpsGatePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-background text-muted-foreground text-sm">
          Loading…
        </div>
      }
    >
      <BusinessOpsGateForm />
    </Suspense>
  )
}
