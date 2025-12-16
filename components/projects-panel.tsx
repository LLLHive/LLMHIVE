"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"
import { Plus, FolderOpen, MessageSquare, FileText, Trash2, MoreHorizontal } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import type { Project } from "@/lib/types"
import { sendDebugLog } from "@/lib/debug-log"

interface ProjectsPanelProps {
  projects: Project[]
  onCreateProject: (project: Omit<Project, "id" | "createdAt">) => void
  onDeleteProject: (id: string) => void
  onSelectProject: (id: string) => void
}

export function ProjectsPanel({ projects, onCreateProject, onDeleteProject, onSelectProject }: ProjectsPanelProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState("")
  const [newProjectDescription, setNewProjectDescription] = useState("")

  // #region agent log
  useEffect(() => {
    if (typeof window === "undefined") return
    sendDebugLog({
      sessionId: "debug-session",
      runId: "pre-fix",
      hypothesisId: "H2",
      location: "projects-panel.tsx:DialogContent",
      message: "Projects dialog rendered",
      data: { isCreating, hasDescription: false },
    })
  }, [isCreating])
  // #endregion

  const handleCreate = () => {
    if (!newProjectName.trim()) return

    onCreateProject({
      name: newProjectName,
      description: newProjectDescription,
      conversations: [],
      files: [],
    })

    setNewProjectName("")
    setNewProjectDescription("")
    setIsCreating(false)
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-start">
        <Dialog open={isCreating} onOpenChange={setIsCreating}>
          <DialogTrigger asChild>
            <Button size="sm" className="bronze-gradient">
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription className="sr-only">
                Provide a project name and optional description to create it.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Project Name</label>
                <Input
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="My Awesome Project"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Description</label>
                <Textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  placeholder="Describe your project..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreating(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={!newProjectName.trim()} className="bronze-gradient">
                Create Project
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <ScrollArea className="h-[calc(100vh-200px)]">
        {projects.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground">
            <FolderOpen className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No projects yet</p>
            <p className="text-xs mt-1">Create a project to organize your work</p>
          </div>
        ) : (
          <div className="space-y-2">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onSelect={() => onSelectProject(project.id)}
                onDelete={() => onDeleteProject(project.id)}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}

function ProjectCard({
  project,
  onSelect,
  onDelete,
}: {
  project: Project
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <div
      onClick={onSelect}
      className="p-4 rounded-lg border border-border bg-card hover:border-[var(--bronze)] transition-colors cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
            <FolderOpen className="h-4 w-4 text-background" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">{project.name}</h3>
            <p className="text-xs text-muted-foreground line-clamp-1">{project.description}</p>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
              className="text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <MessageSquare className="h-3 w-3" />
          {project.conversations.length} chats
        </div>
        <div className="flex items-center gap-1">
          <FileText className="h-3 w-3" />
          {project.files.length} files
        </div>
      </div>
    </div>
  )
}
