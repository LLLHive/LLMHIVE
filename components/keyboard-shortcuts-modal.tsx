"use client"

import { useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Keyboard } from "lucide-react"
import { sendDebugLog } from "@/lib/debug-log"

interface KeyboardShortcutsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface ShortcutItem {
  keys: string[]
  description: string
  category: string
}

const shortcuts: ShortcutItem[] = [
  // Navigation
  { keys: ["⌘", "N"], description: "New chat", category: "Navigation" },
  { keys: ["⌘", "K"], description: "Focus search", category: "Navigation" },
  { keys: ["⌘", "/"], description: "Show shortcuts", category: "Navigation" },
  { keys: ["Esc"], description: "Close modal / Cancel", category: "Navigation" },
  
  // Chat
  { keys: ["⌘", "Enter"], description: "Send message", category: "Chat" },
  { keys: ["Shift", "Enter"], description: "New line", category: "Chat" },
  { keys: ["⌘", "Shift", "V"], description: "Toggle voice input", category: "Chat" },
  
  // Actions
  { keys: ["⌘", "S"], description: "Save settings", category: "Actions" },
  { keys: ["⌘", "E"], description: "Export conversation", category: "Actions" },
  { keys: ["⌘", ","], description: "Open settings", category: "Actions" },
]

const categories = [...new Set(shortcuts.map((s) => s.category))]

export function KeyboardShortcutsModal({ open, onOpenChange }: KeyboardShortcutsModalProps) {
  const isMac = typeof navigator !== "undefined" && navigator.platform.toUpperCase().indexOf("MAC") >= 0
  
  const formatKey = (key: string): string => {
    if (!isMac) {
      return key.replace("⌘", "Ctrl").replace("⌥", "Alt")
    }
    return key
  }

  // #region agent log
  useEffect(() => {
    if (typeof window === "undefined") return
    sendDebugLog({
      sessionId: "debug-session",
      runId: "pre-fix",
      hypothesisId: "H1",
      location: "keyboard-shortcuts-modal.tsx:DialogContent",
      message: "Keyboard shortcuts dialog rendered",
      data: { open, hasDescription: false },
    })
  }, [open])
  // #endregion

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Keyboard className="h-5 w-5 text-[var(--bronze)]" />
            Keyboard Shortcuts
          </DialogTitle>
          <DialogDescription className="sr-only">
            Reference of available keyboard shortcuts.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {categories.map((category) => (
            <div key={category}>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3">{category}</h3>
              <div className="space-y-2">
                {shortcuts
                  .filter((s) => s.category === category)
                  .map((shortcut, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/30"
                    >
                      <span className="text-sm">{shortcut.description}</span>
                      <div className="flex items-center gap-1">
                        {shortcut.keys.map((key, keyIdx) => (
                          <Badge
                            key={keyIdx}
                            variant="outline"
                            className="px-2 py-0.5 text-xs font-mono bg-background"
                          >
                            {formatKey(key)}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>

        <div className="text-xs text-muted-foreground text-center pt-4 border-t border-border">
          Press <Badge variant="outline" className="mx-1 px-1.5 py-0 text-xs font-mono">Esc</Badge> to close
        </div>
      </DialogContent>
    </Dialog>
  )
}

