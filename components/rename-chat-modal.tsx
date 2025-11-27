"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"

interface RenameChatModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentTitle: string
  onRename: (newTitle: string) => void
}

export function RenameChatModal({ open, onOpenChange, currentTitle, onRename }: RenameChatModalProps) {
  const [title, setTitle] = useState(currentTitle)

  useEffect(() => {
    setTitle(currentTitle)
  }, [currentTitle])

  const handleRename = () => {
    if (title.trim()) {
      onRename(title.trim())
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Rename Chat</DialogTitle>
        </DialogHeader>

        <div className="mt-4">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter chat title"
            className="bg-secondary border-border focus:border-[var(--bronze)]"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleRename()
              }
            }}
          />
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleRename} disabled={!title.trim()} className="bronze-gradient">
            Rename
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
