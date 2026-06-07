"use client"

import { useEffect, useRef } from "react"
import { pushGtmPurchase, type GtmPurchasePayload } from "@/lib/marketing/gtm-events"
import { isGtmEnabled } from "@/lib/marketing/gtm"

type Props = {
  purchase: GtmPurchasePayload | null
  enabled: boolean
}

/** Fires GTM `purchase` on /billing/success once Stripe session is verified. */
export function BillingPurchaseTracking({ purchase, enabled }: Props) {
  const trackedRef = useRef(false)

  useEffect(() => {
    if (!enabled || !purchase || trackedRef.current || !isGtmEnabled()) return
    trackedRef.current = true
    pushGtmPurchase(purchase)
  }, [enabled, purchase])

  return null
}
