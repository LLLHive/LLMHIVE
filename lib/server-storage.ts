/**
 * Server-side storage utilities for settings persistence.
 * 
 * Uses cookies for persistence across serverless cold starts.
 * Works alongside client-side localStorage for the best UX.
 */

import { cookies } from 'next/headers'

const SETTINGS_COOKIE_NAME = 'llmhive-settings'
const CRITERIA_COOKIE_NAME = 'llmhive-criteria'
const MAX_COOKIE_AGE = 60 * 60 * 24 * 365 // 1 year

export interface CriteriaSettings {
  accuracy: number
  speed: number
  creativity: number
}

export interface ServerSettings {
  orchestratorSettings?: Record<string, unknown>
  criteriaSettings?: CriteriaSettings
  preferences?: Record<string, unknown>
}

/**
 * Read settings from cookies (server-side).
 */
export async function getServerSettings(userId: string = 'default'): Promise<ServerSettings> {
  try {
    const cookieStore = await cookies()
    const settingsCookie = cookieStore.get(`${SETTINGS_COOKIE_NAME}-${userId}`)
    
    if (settingsCookie?.value) {
      return JSON.parse(decodeURIComponent(settingsCookie.value))
    }
  } catch (error) {
    console.warn('[server-storage] Failed to read settings cookie:', error)
  }
  
  return {
    criteriaSettings: {
      accuracy: 70,
      speed: 70,
      creativity: 50,
    },
  }
}

/**
 * Save settings to cookies (server-side).
 */
export async function setServerSettings(
  userId: string = 'default',
  settings: ServerSettings
): Promise<void> {
  try {
    const cookieStore = await cookies()
    const value = encodeURIComponent(JSON.stringify(settings))
    
    // Check cookie size limit (~4KB)
    if (value.length > 4000) {
      console.warn('[server-storage] Settings too large for cookie, truncating')
      // Store only essential settings
      const essentialSettings: ServerSettings = {
        criteriaSettings: settings.criteriaSettings,
      }
      cookieStore.set(`${SETTINGS_COOKIE_NAME}-${userId}`, encodeURIComponent(JSON.stringify(essentialSettings)), {
        maxAge: MAX_COOKIE_AGE,
        path: '/',
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production',
      })
    } else {
      cookieStore.set(`${SETTINGS_COOKIE_NAME}-${userId}`, value, {
        maxAge: MAX_COOKIE_AGE,
        path: '/',
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production',
      })
    }
  } catch (error) {
    console.error('[server-storage] Failed to save settings cookie:', error)
    throw error
  }
}

/**
 * Get criteria settings from cookie.
 */
export async function getCriteriaSettings(userId: string = 'default'): Promise<CriteriaSettings> {
  const settings = await getServerSettings(userId)
  return settings.criteriaSettings || {
    accuracy: 70,
    speed: 70,
    creativity: 50,
  }
}

/**
 * Save criteria settings to cookie.
 */
export async function setCriteriaSettings(
  userId: string = 'default',
  criteria: CriteriaSettings
): Promise<void> {
  const existing = await getServerSettings(userId)
  await setServerSettings(userId, {
    ...existing,
    criteriaSettings: criteria,
  })
}
