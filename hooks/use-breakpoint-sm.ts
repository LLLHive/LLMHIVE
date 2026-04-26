"use client"

import { useSyncExternalStore } from "react"

/** Tailwind `sm` breakpoint (640px). */
const SM_QUERY = "(min-width: 640px)"

function subscribeSm(onStoreChange: () => void) {
  if (typeof window === "undefined") return () => {}
  const mq = window.matchMedia(SM_QUERY)
  mq.addEventListener("change", onStoreChange)
  return () => mq.removeEventListener("change", onStoreChange)
}

function getSmSnapshot() {
  if (typeof window === "undefined") return true
  return window.matchMedia(SM_QUERY).matches
}

/** True when viewport is `sm` and up (matches Tailwind `sm:`). SSR defaults to true. */
export function useBreakpointSm(): boolean {
  return useSyncExternalStore(subscribeSm, getSmSnapshot, () => true)
}
