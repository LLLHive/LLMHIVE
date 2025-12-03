/**
 * Centralized route definitions for LLMHive.
 * 
 * Use these constants instead of hardcoding paths.
 * This provides type safety and makes refactoring easier.
 */

export const ROUTES = {
  HOME: "/",
  DISCOVER: "/discover",
  ORCHESTRATION: "/orchestration",
  SETTINGS: "/settings",
} as const

export const API_ROUTES = {
  CHAT: "/api/chat",
  AGENTS: "/api/agents",
  EXECUTE: "/api/execute",
  SETTINGS: "/api/settings",
  CRITERIA: "/api/criteria",
  REASONING_CONFIG: "/api/reasoning-config",
} as const

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES]
export type ApiRoute = (typeof API_ROUTES)[keyof typeof API_ROUTES]

/**
 * Helper to check if a path matches a route.
 */
export function isRoute(path: string, route: AppRoute): boolean {
  return path === route || path.startsWith(route + "/")
}

