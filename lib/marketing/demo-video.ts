import { MARKETING_FEATURED_LINE } from "@/lib/marketing/featured-models"
import { BENCHMARK_CLAIM_SHORT } from "@/lib/benchmark-claim"

export type DemoChapter = {
  id: string
  title: string
  start: number
}

export const DEMO_VIDEO = {
  src: "/videos/llmhive-product-demo.mp4",
  poster: "/videos/llmhive-product-demo.jpg",
  captions: "/videos/llmhive-product-demo.vtt",
  duration: 48,
  title: "LLMHive product demo",
  description:
    "A 60-second look at how LLMHive routes one question across frontier models and returns a single best answer.",
  modelsLine: MARKETING_FEATURED_LINE,
  claim: BENCHMARK_CLAIM_SHORT,
  chapters: [
    { id: "intro", title: "Introduction", start: 0 },
    { id: "problem", title: "The problem", start: 8 },
    { id: "hive", title: "One hive", start: 16 },
    { id: "proof", title: "Proof", start: 24 },
    { id: "plans", title: "Plans", start: 32 },
    { id: "cta", title: "Get started", start: 40 },
  ] satisfies DemoChapter[],
  stills: [
    { src: "/videos/frames/01-intro.jpg", start: 0, duration: 8 },
    { src: "/videos/frames/02-problem.jpg", start: 8, duration: 8 },
    { src: "/videos/frames/03-hive.jpg", start: 16, duration: 8 },
    { src: "/videos/frames/04-proof.jpg", start: 24, duration: 8 },
    { src: "/videos/frames/05-plans.jpg", start: 32, duration: 8 },
    { src: "/videos/frames/06-cta.jpg", start: 40, duration: 8 },
  ],
} as const

export function formatDemoTime(seconds: number): string {
  const clamped = Math.max(0, Math.floor(seconds))
  const m = Math.floor(clamped / 60)
  const s = clamped % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function chapterAt(time: number): DemoChapter {
  const chapters = DEMO_VIDEO.chapters
  let current = chapters[0]
  for (const chapter of chapters) {
    if (time >= chapter.start) current = chapter
  }
  return current
}
