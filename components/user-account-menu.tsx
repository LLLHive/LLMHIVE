"use client"

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
import { User, CreditCard, Settings, LogOut, LogIn, Github, Chrome } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { ROUTES } from "@/lib/routes"

interface UserAccountMenuProps {
  // Props are now optional since we use the auth context
  user?: {
    name?: string
    email?: string
    image?: string
  } | null
  onSignIn?: () => void
  onSignOut?: () => void
}

export function UserAccountMenu({ user: propUser, onSignIn, onSignOut }: UserAccountMenuProps) {
  const router = useRouter()
  const auth = useAuth()
  
  // Use auth context user if available, fall back to prop user
  const user = auth.user || propUser
  const isLoggedIn = !!user
  
  const handleSignIn = (provider: 'github' | 'google') => {
    auth.signIn(provider)
  }
  
  const handleSignOut = () => {
    auth.signOut()
    onSignOut?.()
  }

  if (!isLoggedIn) {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
      <Button
        variant="ghost"
        size="sm"
        className="gap-2 h-8 px-3 text-xs bg-secondary/50 border border-border rounded-lg text-[var(--bronze)] hover:bg-secondary hover:border-[var(--bronze)]"
      >
        <LogIn className="h-4 w-4" />
        <span className="hidden sm:inline">Sign In</span>
      </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <div className="px-3 py-2">
            <p className="text-sm font-medium">Sign In</p>
            <p className="text-xs text-muted-foreground">Choose your preferred method</p>
          </div>
          <DropdownMenuSeparator />
          <DropdownMenuItem 
            className="gap-2 cursor-pointer"
            onClick={() => handleSignIn('github')}
          >
            <Github className="h-4 w-4" />
            Continue with GitHub
          </DropdownMenuItem>
          <DropdownMenuItem 
            className="gap-2 cursor-pointer"
            onClick={() => handleSignIn('google')}
          >
            <Chrome className="h-4 w-4" />
            Continue with Google
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
          <Avatar className="h-8 w-8 border border-border">
            <AvatarImage src={user.image || undefined} alt={user.name || "User"} />
            <AvatarFallback className="bg-[var(--bronze)]/20 text-[var(--bronze)] text-xs">
              {user.name?.charAt(0)?.toUpperCase() || "U"}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <div className="px-3 py-2">
          <p className="text-sm font-medium truncate">{user.name || "User"}</p>
          <p className="text-xs text-muted-foreground truncate">{user.email}</p>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem 
          className="gap-2 cursor-pointer"
          onClick={() => router.push(ROUTES.SETTINGS)}
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
        <DropdownMenuItem onClick={handleSignOut} className="gap-2 cursor-pointer text-destructive">
          <LogOut className="h-4 w-4" />
          Sign Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
