import { NextRequest, NextResponse } from "next/server"

/**
 * Comprehensive settings persistence API.
 * 
 * Stores and retrieves all user settings including:
 * - Orchestrator settings (reasoning mode, domain pack, agent mode, tuning options)
 * - Criteria equaliser settings
 * - Advanced features
 * - User preferences
 * 
 * Environment variables:
 * - DATABASE_URL: Connection string for database (if using database storage)
 * - REDIS_URL: Connection string for Redis (if using Redis storage)
 * 
 * TODO: Implement actual database/Redis storage. Currently uses in-memory storage.
 */

// In-memory storage (replace with database/Redis in production)
interface UserSettings {
  orchestratorSettings: {
    reasoningMode: string
    domainPack: string
    agentMode: string
    promptOptimization: boolean
    outputValidation: boolean
    answerStructure: boolean
    sharedMemory: boolean
    learnFromChat: boolean
    selectedModels: string[]
    advancedReasoningMethods: string[]
    advancedFeatures: string[]
  }
  criteriaSettings: {
    accuracy: number
    speed: number
    creativity: number
  }
  preferences: {
    incognitoMode: boolean
    theme: string
    language: string
  }
}

const settingsStorage = new Map<string, UserSettings>()

export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams
    const userId = searchParams.get("userId") || "default"
    const settingType = searchParams.get("type") // "all", "orchestrator", "criteria", "preferences"

    const userSettings = settingsStorage.get(userId) || {
      orchestratorSettings: {
        reasoningMode: "standard",
        domainPack: "default",
        agentMode: "team",
        promptOptimization: false,
        outputValidation: false,
        answerStructure: false,
        sharedMemory: false,
        learnFromChat: false,
        selectedModels: ["gpt-4o-mini"],
        advancedReasoningMethods: [],
        advancedFeatures: [],
      },
      criteriaSettings: {
        accuracy: 70,
        speed: 70,
        creativity: 50,
      },
      preferences: {
        incognitoMode: false,
        theme: "dark",
        language: "en",
      },
    }

    if (settingType === "orchestrator") {
      return NextResponse.json({
        success: true,
        settings: userSettings.orchestratorSettings,
      })
    } else if (settingType === "criteria") {
      return NextResponse.json({
        success: true,
        settings: userSettings.criteriaSettings,
      })
    } else if (settingType === "preferences") {
      return NextResponse.json({
        success: true,
        settings: userSettings.preferences,
      })
    }

    return NextResponse.json({
      success: true,
      settings: userSettings,
    })
  } catch (error: any) {
    console.error("[settings] GET error:", error)
    return NextResponse.json(
      { success: false, error: error.message || "Failed to retrieve settings" },
      { status: 500 }
    )
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { userId = "default", orchestratorSettings, criteriaSettings, preferences } = body

    // Get existing settings or create new
    const existing = settingsStorage.get(userId) || {
      orchestratorSettings: {},
      criteriaSettings: {},
      preferences: {},
    }

    // Merge new settings
    const updated: UserSettings = {
      orchestratorSettings: orchestratorSettings
        ? { ...existing.orchestratorSettings, ...orchestratorSettings }
        : existing.orchestratorSettings,
      criteriaSettings: criteriaSettings
        ? { ...existing.criteriaSettings, ...criteriaSettings }
        : existing.criteriaSettings,
      preferences: preferences
        ? { ...existing.preferences, ...preferences }
        : existing.preferences,
    }

    // Validate criteria settings
    if (updated.criteriaSettings.accuracy !== undefined) {
      if (updated.criteriaSettings.accuracy < 0 || updated.criteriaSettings.accuracy > 100) {
        return NextResponse.json(
          { success: false, error: "Invalid accuracy value (must be 0-100)" },
          { status: 400 }
        )
      }
    }
    if (updated.criteriaSettings.speed !== undefined) {
      if (updated.criteriaSettings.speed < 0 || updated.criteriaSettings.speed > 100) {
        return NextResponse.json(
          { success: false, error: "Invalid speed value (must be 0-100)" },
          { status: 400 }
        )
      }
    }
    if (updated.criteriaSettings.creativity !== undefined) {
      if (updated.criteriaSettings.creativity < 0 || updated.criteriaSettings.creativity > 100) {
        return NextResponse.json(
          { success: false, error: "Invalid creativity value (must be 0-100)" },
          { status: 400 }
        )
      }
    }

    // Store settings
    settingsStorage.set(userId, updated)

    // TODO: Persist to database/Redis
    // Example:
    // await db.userSettings.upsert({
    //   where: { userId },
    //   update: updated,
    //   create: { userId, ...updated },
    // })

    return NextResponse.json({
      success: true,
      message: "Settings saved successfully",
      settings: updated,
    })
  } catch (error: any) {
    console.error("[settings] POST error:", error)
    return NextResponse.json(
      { success: false, error: error.message || "Failed to save settings" },
      { status: 500 }
    )
  }
}

