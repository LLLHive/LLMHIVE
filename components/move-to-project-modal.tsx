"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { FolderOpen, Plus, Check } from "lucide-react"
import type { Project } from "@/lib/types"

interface MoveToProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projects: Project[]
  onMove: (projectId: string) => void
  onCreateProject?: () => void
}

export function MoveToProjectModal({ open, onOpenChange, projects, onMove, onCreateProject }: MoveToProjectModalProps) {
  const [selectedProject, setSelectedProject] = useState<string | null>(null)

  const handleMove = () => {
    if (selectedProject) {
      onMove(selectedProject)
      onOpenChange(false)
      setSelectedProject(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Move to Project</DialogTitle>
        </DialogHeader>

        <ScrollArea className="max-h-60 mt-4">
          {projects.length === 0 ? (
            <div className="text-center py-8">
              <FolderOpen className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground mb-4">No projects yet</p>
              {onCreateProject && (
                <Button variant="outline" size="sm" onClick={onCreateProject} className="gap-2 bg-transparent">
                  <Plus className="h-4 w-4" />
                  Create Project
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => setSelectedProject(project.id)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-colors text-left ${
                    selectedProject === project.id
                      ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                      : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                  }`}
                >
                  <FolderOpen className="h-5 w-5 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{project.name}</p>
                    <p className="text-xs text-muted-foreground truncate">{project.description}</p>
                  </div>
                  {selectedProject === project.id && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                </button>
              ))}
            </div>
          )}
        </ScrollArea>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleMove} disabled={!selectedProject} className="bronze-gradient">
            Move
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
