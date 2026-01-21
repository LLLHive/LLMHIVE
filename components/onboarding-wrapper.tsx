"use client"

import { useUser } from "@clerk/nextjs"
import { OnboardingModal } from "@/components/onboarding-modal"

/**
 * OnboardingWrapper - Renders the onboarding modal for authenticated users
 * 
 * This wrapper component checks if the user is authenticated before
 * showing the onboarding flow, ensuring a personalized experience.
 */
export function OnboardingWrapper() {
  const { isSignedIn, user, isLoaded } = useUser()

  // Don't show onboarding for unauthenticated users or while loading
  if (!isLoaded || !isSignedIn || !user) {
    return null
  }

  // Get user's display name
  const displayName = user.firstName 
    ? `${user.firstName}${user.lastName ? ` ${user.lastName}` : ""}` 
    : user.emailAddresses?.[0]?.emailAddress?.split("@")[0] 
    || "there"

  return <OnboardingModal userName={displayName} />
}
