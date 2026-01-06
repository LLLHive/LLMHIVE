"use client"

import dynamic from "next/dynamic"

const ForestBackground = dynamic(
  () => import("@/components/forest-background").then(m => m.ForestBackground),
  { ssr: false }
)

export function ForestBackgroundWrapper() {
  return <ForestBackground />
}

