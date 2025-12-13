"use client"

import { useEffect } from "react"

const STORAGE_KEY = "llmhive-appearance-settings"

/**
 * Applies appearance settings from localStorage on initial load
 * This ensures settings like Compact Mode and Animations persist across page loads
 */
export function AppearanceSettingsLoader() {
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const settings = JSON.parse(saved) as string[]
        
        // Apply compact mode
        if (settings.includes("compactMode")) {
          document.documentElement.classList.add("compact-mode")
        } else {
          document.documentElement.classList.remove("compact-mode")
        }
        
        // Apply animations (disabled if NOT in list)
        if (!settings.includes("animations")) {
          document.documentElement.classList.add("no-animations")
        } else {
          document.documentElement.classList.remove("no-animations")
        }
      }
    } catch (e) {
      console.error("Failed to load appearance settings:", e)
    }
  }, [])

  return null
}

