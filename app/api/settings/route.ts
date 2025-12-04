import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"

/**
 * Comprehensive settings persistence API.
 * 
 * Stores and retrieves all user settings including:
 * - Orchestrator settings (reasoning mode, domain pack, agent mode, tuning options)
 * - Criteria equaliser settings
 * - Advanced features
 * - User preferences
 * 
 * Uses cookies for persistence across serverless cold starts.
 */

const SETTINGS_COOKIE_NAME = "llmhive-settings"
const MAX_COOKIE_AGE = 60 * 60 * 24 * 365 // 1 year

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

const DEFAULT_SETTINGS: UserSettings = {
  orchestratorSettings: {
    reasoningMode: "standard",
    domainPack: "default",
    agentMode: "team",
    promptOptimization: true,
    outputValidation: true,
    answerStructure: true,
    sharedMemory: false,
    learnFromChat: false,
    selectedModels: ["automatic"],
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

async function getSettingsFromCookie(userId: string): Promise<UserSettings> {
  try {
    const cookieStore = await cookies()
    const cookie = cookieStore.get(`${SETTINGS_COOKIE_NAME}-${userId}`)
    
    if (cookie?.value) {
      const parsed = JSON.parse(decodeURIComponent(cookie.value))
      // Merge with defaults to ensure all fields exist
      return {
        orchestratorSettings: { ...DEFAULT_SETTINGS.orchestratorSettings, ...parsed.orchestratorSettings },
        criteriaSettings: { ...DEFAULT_SETTINGS.criteriaSettings, ...parsed.criteriaSettings },
        preferences: { ...DEFAULT_SETTINGS.preferences, ...parsed.preferences },
      }
    }
  } catch (error) {
    console.warn("[settings] Failed to read cookie:", error)
  }
  
  return DEFAULT_SETTINGS
}

async function saveSettingsToCookie(userId: string, settings: UserSettings): Promise<void> {
  const cookieStore = await cookies()
  const value = encodeURIComponent(JSON.stringify(settings))
  
  // Cookies have a ~4KB limit - if exceeded, store only essential data
  if (value.length > 4000) {
    console.warn("[settings] Settings too large for cookie, storing essential only")
    const essential = {
      criteriaSettings: settings.criteriaSettings,
      orchestratorSettings: {
        reasoningMode: settings.orchestratorSettings.reasoningMode,
        selectedModels: settings.orchestratorSettings.selectedModels?.slice(0, 5),
      },
    }
    cookieStore.set(`${SETTINGS_COOKIE_NAME}-${userId}`, encodeURIComponent(JSON.stringify(essential)), {
      maxAge: MAX_COOKIE_AGE,
      path: "/",
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    })
  } else {
    cookieStore.set(`${SETTINGS_COOKIE_NAME}-${userId}`, value, {
      maxAge: MAX_COOKIE_AGE,
      path: "/",
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    })
  }
}

export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams
    const userId = searchParams.get("userId") || "default"
    const settingType = searchParams.get("type") // "all", "orchestrator", "criteria", "preferences"

    const userSettings = await getSettingsFromCookie(userId)

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
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to retrieve settings"
    console.error("[settings] GET error:", error)
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    )
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { userId = "default", orchestratorSettings, criteriaSettings, preferences } = body

    // Get existing settings
    const existing = await getSettingsFromCookie(userId)

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

    // Persist to cookie
    await saveSettingsToCookie(userId, updated)

    return NextResponse.json({
      success: true,
      message: "Settings saved successfully",
      settings: updated,
    })
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to save settings"
    console.error("[settings] POST error:", error)
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    )
  }
}

