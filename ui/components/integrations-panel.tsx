"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Github, Cloud, Box, CheckCircle2, XCircle } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import type { Integration } from "@/lib/types"

const availableIntegrations = [
  {
    id: "github",
    name: "GitHub",
    icon: Github,
    description: "Connect repositories for code analysis and PR generation",
    fields: [
      { key: "token", label: "Personal Access Token", type: "password" },
      { key: "repo", label: "Repository (org/repo)", type: "text" },
    ],
  },
  {
    id: "google-cloud",
    name: "Google Cloud",
    icon: Cloud,
    description: "Access BigQuery, Cloud Storage, and AI services",
    fields: [
      { key: "projectId", label: "Project ID", type: "text" },
      { key: "credentials", label: "Service Account JSON", type: "textarea" },
    ],
  },
  {
    id: "vercel",
    name: "Vercel",
    icon: Box,
    description: "Deploy and manage projects directly from chat",
    fields: [{ key: "token", label: "Vercel Token", type: "password" }],
  },
]

export function IntegrationsPanel() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [configuring, setConfiguring] = useState<string | null>(null)

  const handleConnect = (id: string, config: Record<string, any>) => {
    setIntegrations((prev) => [
      ...prev.filter((i) => i.id !== id),
      { id: id as any, name: id as any, connected: true, config },
    ])
    setConfiguring(null)
  }

  const handleDisconnect = (id: string) => {
    setIntegrations((prev) => prev.filter((i) => i.id !== id))
  }

  return (
    <div className="space-y-4">
      {availableIntegrations.map((integration) => {
        const connected = integrations.find((i) => i.id === integration.id)
        const Icon = integration.icon

        return (
          <div key={integration.id} className="p-4 rounded-lg border border-border bg-card">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold">{integration.name}</h4>
                    {connected ? (
                      <Badge variant="outline" className="text-green-500 border-green-500 gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Connected
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-muted-foreground gap-1">
                        <XCircle className="h-3 w-3" />
                        Not Connected
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">{integration.description}</p>
                </div>
              </div>
              <div className="flex gap-2">
                {connected ? (
                  <Button size="sm" variant="outline" onClick={() => handleDisconnect(integration.id)}>
                    Disconnect
                  </Button>
                ) : (
                  <Dialog
                    open={configuring === integration.id}
                    onOpenChange={(open) => setConfiguring(open ? integration.id : null)}
                  >
                    <DialogTrigger asChild>
                      <Button size="sm" variant="outline">
                        Connect
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Connect {integration.name}</DialogTitle>
                      </DialogHeader>
                      <IntegrationForm integration={integration} onConnect={handleConnect} />
                    </DialogContent>
                  </Dialog>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function IntegrationForm({
  integration,
  onConnect,
}: {
  integration: (typeof availableIntegrations)[0]
  onConnect: (id: string, config: Record<string, any>) => void
}) {
  const [config, setConfig] = useState<Record<string, any>>({})

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onConnect(integration.id, config)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {integration.fields.map((field) => (
        <div key={field.key} className="space-y-2">
          <Label htmlFor={field.key}>{field.label}</Label>
          {field.type === "textarea" ? (
            <textarea
              id={field.key}
              className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={config[field.key] || ""}
              onChange={(e) => setConfig({ ...config, [field.key]: e.target.value })}
              required
            />
          ) : (
            <Input
              id={field.key}
              type={field.type}
              value={config[field.key] || ""}
              onChange={(e) => setConfig({ ...config, [field.key]: e.target.value })}
              required
            />
          )}
        </div>
      ))}
      <Button type="submit" className="w-full">
        Connect
      </Button>
    </form>
  )
}
