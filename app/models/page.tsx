"use client"

/**
 * Models Page
 * 
 * Combined view for:
 * - Model Explorer
 * - Rankings & Insights
 * - Prompt Playground
 */

import * as React from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Search, BarChart3, Wand2 } from "lucide-react"

import { ModelExplorer } from "@/components/openrouter/model-explorer"
import { RankingsInsights } from "@/components/openrouter/rankings-insights"
import { PromptPlayground } from "@/components/openrouter/prompt-playground"
import type { OpenRouterModel } from "@/lib/openrouter/types"

export default function ModelsPage() {
  const [activeTab, setActiveTab] = React.useState("explore")
  const [selectedModel, setSelectedModel] = React.useState<OpenRouterModel>()
  const [showModelSelector, setShowModelSelector] = React.useState(false)
  
  const handleSelectModel = (model: OpenRouterModel) => {
    setSelectedModel(model)
    
    // If coming from rankings or explore, go to playground
    if (activeTab !== "playground") {
      setActiveTab("playground")
    }
    
    setShowModelSelector(false)
  }
  
  return (
    <div className="h-full flex flex-col">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <div className="border-b px-4 bg-background">
          <TabsList className="h-14">
            <TabsTrigger value="explore" className="gap-2 px-4">
              <Search className="w-4 h-4" />
              <span>Explore Models</span>
            </TabsTrigger>
            <TabsTrigger value="rankings" className="gap-2 px-4">
              <BarChart3 className="w-4 h-4" />
              <span>Rankings</span>
            </TabsTrigger>
            <TabsTrigger value="playground" className="gap-2 px-4">
              <Wand2 className="w-4 h-4" />
              <span>Playground</span>
            </TabsTrigger>
          </TabsList>
        </div>
        
        <TabsContent value="explore" className="flex-1 mt-0 overflow-hidden">
          <ModelExplorer
            onSelectModel={handleSelectModel}
            selectedModelId={selectedModel?.id}
          />
        </TabsContent>
        
        <TabsContent value="rankings" className="flex-1 mt-0 overflow-hidden">
          <RankingsInsights
            onSelectModel={handleSelectModel}
          />
        </TabsContent>
        
        <TabsContent value="playground" className="flex-1 mt-0 overflow-hidden">
          <PromptPlayground
            selectedModel={selectedModel}
            onChangeModel={() => setShowModelSelector(true)}
          />
        </TabsContent>
      </Tabs>
      
      {/* Model selector dialog */}
      <Dialog open={showModelSelector} onOpenChange={setShowModelSelector}>
        <DialogContent className="max-w-4xl h-[80vh] p-0 overflow-hidden">
          <ModelExplorer
            onSelectModel={handleSelectModel}
            selectedModelId={selectedModel?.id}
            showComparison={false}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}

