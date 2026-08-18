"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Captions,
  Maximize,
  Minimize,
  Pause,
  Play,
  Volume2,
  VolumeX,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  DEMO_VIDEO,
  chapterAt,
  formatDemoTime,
  type DemoChapter,
} from "@/lib/marketing/demo-video"

type ProductDemoPlayerProps = {
  className?: string
  autoPlay?: boolean
  compact?: boolean
}

export default function ProductDemoPlayer({
  className,
  autoPlay = false,
  compact = false,
}: ProductDemoPlayerProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const [useVideo, setUseVideo] = useState(true)
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(true)
  const [captions, setCaptions] = useState(true)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState<number>(DEMO_VIDEO.duration)
  const [fullscreen, setFullscreen] = useState(false)
  const filmStartedAt = useRef<number | null>(null)
  const filmOffset = useRef(0)

  const activeChapter = useMemo(() => chapterAt(currentTime), [currentTime])
  const progress = duration > 0 ? Math.min(1, currentTime / duration) : 0

  const seek = useCallback(
    (time: number) => {
      const next = Math.min(duration, Math.max(0, time))
      if (useVideo && videoRef.current) {
        videoRef.current.currentTime = next
      } else {
        filmOffset.current = next
        filmStartedAt.current = playing ? performance.now() - next * 1000 : null
      }
      setCurrentTime(next)
    },
    [duration, playing, useVideo],
  )

  const togglePlay = useCallback(() => {
    if (useVideo && videoRef.current) {
      if (videoRef.current.paused) void videoRef.current.play()
      else videoRef.current.pause()
      return
    }
    setPlaying((was) => {
      if (was) {
        filmOffset.current = currentTime
        filmStartedAt.current = null
        return false
      }
      if (currentTime >= duration - 0.15) {
        filmOffset.current = 0
        setCurrentTime(0)
      }
      filmStartedAt.current = performance.now() - filmOffset.current * 1000
      return true
    })
  }, [currentTime, duration, useVideo])

  useEffect(() => {
    if (useVideo || !playing) return
    let frame = 0
    const tick = (now: number) => {
      const started = filmStartedAt.current ?? now
      filmStartedAt.current = started
      const t = (now - started) / 1000
      if (t >= duration) {
        setCurrentTime(duration)
        setPlaying(false)
        filmOffset.current = 0
        filmStartedAt.current = null
        return
      }
      setCurrentTime(t)
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [duration, playing, useVideo])

  useEffect(() => {
    if (!autoPlay) return
    const id = window.setTimeout(() => {
      if (useVideo && videoRef.current) void videoRef.current.play().catch(() => {})
      else setPlaying(true)
    }, 400)
    return () => window.clearTimeout(id)
  }, [autoPlay, useVideo])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!rootRef.current?.contains(document.activeElement) && document.activeElement !== document.body) {
        return
      }
      if (event.key === " " || event.key === "k") {
        event.preventDefault()
        togglePlay()
      }
      if (event.key === "ArrowRight") seek(currentTime + 5)
      if (event.key === "ArrowLeft") seek(currentTime - 5)
      if (event.key === "m") setMuted((v) => !v)
      if (event.key === "f") void toggleFullscreen()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [currentTime, seek, togglePlay])

  const toggleFullscreen = async () => {
    const node = rootRef.current
    if (!node) return
    if (document.fullscreenElement) {
      await document.exitFullscreen()
      setFullscreen(false)
    } else {
      await node.requestFullscreen()
      setFullscreen(true)
    }
  }

  const caption = captionAt(currentTime)

  return (
    <div className={cn("w-full", className)}>
      <div
        ref={rootRef}
        className="group relative aspect-video overflow-hidden rounded-2xl border border-[#262626] bg-black shadow-[0_30px_80px_-40px_rgba(196,142,72,0.45)]"
        tabIndex={0}
      >
        {useVideo ? (
          <video
            ref={videoRef}
            className="h-full w-full object-cover"
            poster={DEMO_VIDEO.poster}
            playsInline
            preload="metadata"
            muted={muted}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
            onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || DEMO_VIDEO.duration)}
            onEnded={() => {
              setPlaying(false)
              setCurrentTime(0)
            }}
            onError={() => setUseVideo(false)}
          >
            <source src={DEMO_VIDEO.src} type="video/mp4" />
            <track kind="captions" src={DEMO_VIDEO.captions} srcLang="en" label="English" default={captions} />
          </video>
        ) : (
          <FilmStage currentTime={currentTime} playing={playing} />
        )}

        {!playing && currentTime < 0.2 && (
          <button
            type="button"
            onClick={togglePlay}
            className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/25 text-white"
            aria-label="Play LLMHive product demo"
          >
            <span className="flex h-20 w-20 items-center justify-center rounded-full border border-amber-400/50 bg-amber-500 text-black shadow-lg shadow-amber-500/30 transition hover:scale-105">
              <Play className="ml-1 h-8 w-8 fill-current" />
            </span>
            <span className="mt-4 text-sm font-medium tracking-wide text-white/90">Watch the 60-second demo</span>
          </button>
        )}

        {captions && caption && (playing || currentTime > 0.2) && (
          <div className="pointer-events-none absolute inset-x-0 bottom-20 z-20 px-6 text-center">
            <p className="inline-block max-w-3xl rounded-md bg-black/70 px-4 py-2 text-sm text-white md:text-base">
              {caption}
            </p>
          </div>
        )}

        <div className="absolute inset-x-0 bottom-0 z-30 bg-gradient-to-t from-black/90 via-black/50 to-transparent px-4 pb-3 pt-16 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100 md:focus-within:opacity-100">
          <button
            type="button"
            className="mb-3 h-1.5 w-full rounded-full bg-white/20"
            aria-label="Seek demo"
            onClick={(event) => {
              const rect = event.currentTarget.getBoundingClientRect()
              const ratio = (event.clientX - rect.left) / rect.width
              seek(ratio * duration)
            }}
          >
            <span className="block h-full rounded-full bg-amber-400" style={{ width: `${progress * 100}%` }} />
          </button>
          <div className="flex items-center gap-2 text-white">
            <ControlButton label={playing ? "Pause" : "Play"} onClick={togglePlay}>
              {playing ? <Pause className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 fill-current" />}
            </ControlButton>
            <ControlButton label={muted ? "Unmute" : "Mute"} onClick={() => setMuted((v) => !v)}>
              {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
            </ControlButton>
            <span className="ml-1 text-xs tabular-nums text-white/80">
              {formatDemoTime(currentTime)} / {formatDemoTime(duration)}
            </span>
            <span className="ml-2 hidden text-xs text-amber-300 sm:inline">{activeChapter.title}</span>
            <div className="ml-auto flex items-center gap-1">
              <ControlButton label="Captions" onClick={() => setCaptions((v) => !v)}>
                <Captions className={cn("h-4 w-4", captions && "text-amber-300")} />
              </ControlButton>
              <ControlButton label={fullscreen ? "Exit full screen" : "Full screen"} onClick={() => void toggleFullscreen()}>
                {fullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
              </ControlButton>
            </div>
          </div>
        </div>
      </div>

      {!compact && (
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {DEMO_VIDEO.chapters.map((chapter) => (
            <ChapterChip
              key={chapter.id}
              chapter={chapter}
              active={activeChapter.id === chapter.id}
              onSelect={() => {
                seek(chapter.start)
                if (useVideo && videoRef.current && videoRef.current.paused) {
                  void videoRef.current.play()
                } else if (!useVideo && !playing) {
                  filmOffset.current = chapter.start
                  filmStartedAt.current = performance.now() - chapter.start * 1000
                  setPlaying(true)
                }
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function FilmStage({ currentTime, playing }: { currentTime: number; playing: boolean }) {
  const still =
    DEMO_VIDEO.stills.find((item) => currentTime >= item.start && currentTime < item.start + item.duration) ||
    DEMO_VIDEO.stills[0]
  const local = currentTime - still.start
  const zoom = 1 + Math.min(0.08, (local / still.duration) * 0.08)

  return (
    <div className="absolute inset-0">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={still.src}
        alt=""
        className="h-full w-full object-cover"
        style={{
          transform: `scale(${zoom})`,
          transition: playing ? "transform 120ms linear" : "none",
        }}
      />
    </div>
  )
}

function ControlButton({
  label,
  onClick,
  children,
}: {
  label: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="flex h-8 w-8 items-center justify-center rounded-md text-white hover:bg-white/10"
    >
      {children}
    </button>
  )
}

function ChapterChip({
  chapter,
  active,
  onSelect,
}: {
  chapter: DemoChapter
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex items-center gap-2 rounded-lg px-4 py-2 text-sm transition-colors",
        active
          ? "border border-[#C48E48]/30 bg-[#C48E48]/20 text-[#C48E48]"
          : "bg-[#262626]/50 text-muted-foreground hover:bg-[#262626] hover:text-foreground",
      )}
    >
      <span>{chapter.title}</span>
      <span className="text-xs opacity-60">{formatDemoTime(chapter.start)}</span>
    </button>
  )
}

const CAPTIONS: Array<{ start: number; end: number; text: string }> = [
  { start: 0, end: 8, text: "See LLMHive in action. Premium orchestration for the best AI answers." },
  { start: 8, end: 16, text: "Stop stacking ChatGPT, Claude, Gemini, and Grok — $90+ a month." },
  { start: 16, end: 24, text: "You ask. The hive routes. One verified answer from 350+ models." },
  { start: 24, end: 32, text: "#1 in 5 out of 8 benchmark categories — May 2026." },
  { start: 32, end: 40, text: "Standard $10. Premium $20. Start Standard free for 3 days." },
  { start: 40, end: 48, text: "Less time getting things done. More time for what matters." },
]

function captionAt(time: number): string | null {
  return CAPTIONS.find((item) => time >= item.start && time < item.end)?.text ?? null
}
