"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"

interface RenameProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentName: string
  onRename: (newName: string) => void
}

export function RenameProjectModal({ open, onOpenChange, currentName, onRename }: RenameProjectModalProps) {
  const [name, setName] = useState(currentName)

  useEffect(() => {
    setName(currentName)
  }, [currentName])

  const handleRename = () => {
    if (name.trim()) {
      onRename(name.trim())
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Rename Project</DialogTitle>
          <DialogDescription className="sr-only">
            Enter a new name for this project.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter project name"
            className="bg-secondary border-border focus:border-[var(--bronze)]"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleRename()
              }
            }}
            autoFocus
          />
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleRename} disabled={!name.trim()} className="bronze-gradient">
            Rename
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

