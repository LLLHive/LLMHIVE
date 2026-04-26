/**
 * Lucide icon mapping for OpenRouter category slugs.
 * Shared by chat toolbar, /models page, and any other category UI.
 */

import type { ElementType } from "react"
import {
  BarChart3,
  Code,
  FlaskConical,
  Heart,
  Image as ImageIcon,
  Scale,
  Megaphone,
  Search,
  Cpu,
  Landmark,
  GraduationCap,
  Users,
  MessageSquare,
  Languages,
  Wrench as ToolIcon,
} from "lucide-react"

const CATEGORY_ICONS: Record<string, ElementType> = {
  programming: Code,
  science: FlaskConical,
  health: Heart,
  legal: Scale,
  marketing: Megaphone,
  "marketing/seo": Search,
  "marketing/content": MessageSquare,
  "marketing/social-media": Users,
  technology: Cpu,
  finance: Landmark,
  academia: GraduationCap,
  roleplay: Users,
  "creative-writing": MessageSquare,
  "customer-support": Users,
  translation: Languages,
  "data-analysis": BarChart3,
  "long-context": MessageSquare,
  "tool-use": ToolIcon,
  vision: ImageIcon,
  reasoning: FlaskConical,
}

export function getOpenRouterCategoryIcon(slug: string): ElementType {
  return CATEGORY_ICONS[slug] || BarChart3
}

/** Tailwind gradient classes for category tiles (e.g. models page). */
export const CATEGORY_GRADIENT_BG: Record<string, string> = {
  programming: "from-violet-500 to-purple-500",
  science: "from-cyan-500 to-teal-500",
  health: "from-red-500 to-rose-500",
  legal: "from-gray-500 to-slate-500",
  marketing: "from-orange-500 to-amber-500",
  "marketing/seo": "from-teal-500 to-cyan-500",
  "marketing/content": "from-orange-400 to-amber-500",
  technology: "from-slate-500 to-gray-500",
  finance: "from-emerald-500 to-green-500",
  academia: "from-amber-500 to-yellow-500",
  roleplay: "from-pink-500 to-rose-500",
  translation: "from-sky-500 to-blue-500",
  "creative-writing": "from-purple-500 to-fuchsia-500",
  "customer-support": "from-blue-500 to-indigo-500",
  "data-analysis": "from-indigo-500 to-violet-500",
  reasoning: "from-cyan-600 to-blue-600",
  "tool-use": "from-orange-500 to-red-500",
  vision: "from-fuchsia-500 to-pink-500",
  "long-context": "from-purple-500 to-violet-500",
}

export function getOpenRouterCategoryGradient(slug: string): string {
  return CATEGORY_GRADIENT_BG[slug] || "from-slate-600 to-slate-800"
}
