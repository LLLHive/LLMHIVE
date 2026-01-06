"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { User, CreditCard, Settings, LogOut, LogIn } from "lucide-react"
import { SignInButton, SignOutButton, useUser, useClerk } from "@clerk/nextjs"
import { ROUTES } from "@/lib/routes"

interface UserAccountMenuProps {
  // Props are now optional since we use Clerk
  user?: {
    name?: string
    email?: string
    image?: string
  } | null
  onSignIn?: () => void
  onSignOut?: () => void
}

export function UserAccountMenu({ onSignOut }: UserAccountMenuProps) {
  const router = useRouter()
  const { user, isLoaded, isSignedIn } = useUser()
  const { openUserProfile } = useClerk()
  const [hasHydrated, setHasHydrated] = useState(false)

  useEffect(() => {
    setHasHydrated(true)
  }, [])

  // Show loading state while hydrating or Clerk loads
  if (!hasHydrated || !isLoaded) {
    return (
      <Button
        variant="ghost"
        size="sm"
        disabled
        className="gap-2 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg"
      >
        <div className="h-4 w-4 animate-pulse bg-muted rounded" />
        <span className="hidden sm:inline">Loading...</span>
      </Button>
    )
  }

  // Not signed in - show sign in button
  if (!isSignedIn || !user) {
    return (
      <SignInButton mode="modal">
        <Button
          variant="ghost"
          size="sm"
          className="gap-2 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg text-[var(--bronze)] hover:bg-secondary hover:border-[var(--bronze)]"
        >
          <LogIn className="h-4 w-4" />
          <span className="hidden sm:inline">Sign In</span>
        </Button>
      </SignInButton>
    )
  }

  // Signed in - show user menu
  const displayName = user.fullName || user.firstName || user.username || "User"
  const email = user.primaryEmailAddress?.emailAddress || ""
  const avatarUrl = user.imageUrl

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full" aria-label="Open account menu">
          <Avatar className="h-8 w-8 border border-border">
            <AvatarImage src={avatarUrl} alt={displayName} />
            <AvatarFallback className="bg-[var(--bronze)]/20 text-[var(--bronze)] text-xs">
              {displayName.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <div className="px-3 py-2">
          <p className="text-sm font-medium truncate">{displayName}</p>
          <p className="text-xs text-muted-foreground truncate">{email}</p>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem 
          className="gap-2 cursor-pointer"
          onClick={() => openUserProfile()}
        >
          <User className="h-4 w-4" />
          Account
        </DropdownMenuItem>
        <DropdownMenuItem 
          className="gap-2 cursor-pointer"
          onClick={() => router.push(ROUTES.SETTINGS + '?tab=billing')}
        >
          <CreditCard className="h-4 w-4" />
          Billing
        </DropdownMenuItem>
        <DropdownMenuItem 
          className="gap-2 cursor-pointer"
          onClick={() => router.push(ROUTES.SETTINGS)}
        >
          <Settings className="h-4 w-4" />
          Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <SignOutButton>
          <DropdownMenuItem 
            className="gap-2 cursor-pointer text-destructive"
            onClick={() => onSignOut?.()}
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </DropdownMenuItem>
        </SignOutButton>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
