#!/usr/bin/env python3
"""Render LLMHive marketing demo frames (and optional MP4) from cinematic stills."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STILLS = ROOT / "public" / "videos" / "stills"
FRAMES = ROOT / "public" / "videos" / "frames"
OUT_DIR = ROOT / "public" / "videos"
POSTER = OUT_DIR / "llmhive-product-demo.jpg"
MP4 = OUT_DIR / "llmhive-product-demo.mp4"
WIDTH, HEIGHT = 1920, 1080
BRONZE = (196, 142, 72)
WHITE = (255, 255, 255)
MUTED = (210, 210, 210)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cover(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    src_w, src_h = img.size
    scale = max(WIDTH / src_w, HEIGHT / src_h)
    img = img.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = (img.width - WIDTH) // 2
    top = (img.height - HEIGHT) // 2
    img = img.crop((left, top, left + WIDTH, top + HEIGHT))
    img = ImageEnhance.Brightness(img).enhance(0.62)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    return img.filter(ImageFilter.GaussianBlur(radius=0.4))


def shade(base: Image.Image) -> Image.Image:
    overlay = Image.new("RGB", (WIDTH, HEIGHT), (5, 5, 5))
    return Image.blend(base, overlay, 0.42)


def draw_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] = WHITE,
    max_width: int | None = None,
) -> int:
    x, y = xy
    if max_width is None:
        draw.text((x, y), text, font=font, fill=fill)
        return int(draw.textbbox((x, y), text, font=font)[3])
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    bottom = y
    for line in lines:
        draw.text((x, bottom), line, font=font, fill=fill)
        bottom = int(draw.textbbox((x, bottom), line, font=font)[3]) + 12
    return bottom


def card(
    background: Path,
    *,
    kicker: str,
    title: str,
    subtitle: str,
    footer: str | None = None,
) -> Image.Image:
    img = shade(cover(background)).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle((0, 0, 12, HEIGHT), fill=BRONZE + (255,))
    draw.rectangle((0, HEIGHT - 8, WIDTH, HEIGHT), fill=BRONZE + (255,))
    y = 150
    draw_text(draw, text=kicker.upper(), xy=(96, y), font=_font(28, True), fill=BRONZE)
    y = 230
    y = draw_text(draw, text=title, xy=(96, y), font=_font(78, True), fill=WHITE, max_width=1640)
    y += 28
    draw_text(draw, text=subtitle, xy=(96, y), font=_font(36), fill=MUTED, max_width=1500)
    if footer:
        draw_text(draw, text=footer, xy=(96, HEIGHT - 140), font=_font(28, True), fill=BRONZE)
    logo = ROOT / "public" / "logo.png"
    if logo.exists():
        mark = Image.open(logo).convert("RGBA")
        mark.thumbnail((72, 72), Image.Resampling.LANCZOS)
        img.paste(mark, (WIDTH - 96 - mark.width, 64), mark)
    return img.convert("RGB")


def render_frames() -> list[Path]:
    FRAMES.mkdir(parents=True, exist_ok=True)
    scenes = [
        (
            "01-intro.jpg",
            STILLS / "llmhive-demo-poster.png",
            "Product demo · 60 seconds",
            "See LLMHive in action.",
            "Premium orchestration for the best AI answers.",
            "GPT-5.6 Sol Pro · Claude Opus 5 · Gemini 3.1 Pro · Grok 4.5 · Kimi K3 · 350+ more",
        ),
        (
            "02-problem.jpg",
            STILLS / "llmhive-demo-problem.png",
            "The old way",
            "Stop stacking AI subscriptions.",
            "ChatGPT Plus, Claude Pro, Gemini Advanced, and Grok add up to $90+ every month.",
            "One chat. One bill. The strongest answer.",
        ),
        (
            "03-hive.jpg",
            STILLS / "llmhive-demo-orchestration.png",
            "How LLMHive works",
            "You ask. The hive routes.",
            "Orchestration picks the strongest models for the task, then returns one verified answer.",
            "No tab-switching. No model guesswork.",
        ),
        (
            "04-proof.jpg",
            STILLS / "llmhive-demo-poster.png",
            "Benchmarks · May 2026",
            "#1 in 5 out of 8 categories.",
            "Standard and Premium include premium orchestration. Enterprise adds flagship model pick.",
            "350+ models available to route",
        ),
        (
            "05-plans.jpg",
            STILLS / "llmhive-demo-lifestyle.png",
            "Simple pricing",
            "Standard $10. Premium $20.",
            "Start Standard free for 3 days. Add payment before day 4 to continue — or just go Premium.",
            "llmhive.ai",
        ),
        (
            "06-cta.jpg",
            STILLS / "llmhive-demo-lifestyle.png",
            "Ready when you are",
            "Less time getting things done.",
            "More time for what matters. Start in minutes at llmhive.ai.",
            "Cancel anytime · Flat monthly pricing",
        ),
    ]
    paths: list[Path] = []
    for name, bg, kicker, title, subtitle, footer in scenes:
        if not bg.exists():
            raise FileNotFoundError(f"Missing still: {bg}")
        frame = card(bg, kicker=kicker, title=title, subtitle=subtitle, footer=footer)
        dest = FRAMES / name
        frame.save(dest, "JPEG", quality=88, optimize=True, progressive=True)
        paths.append(dest)
        print(f"wrote {dest.relative_to(ROOT)}")
    poster = Image.open(paths[0]).convert("RGB")
    poster.save(POSTER, "JPEG", quality=88, optimize=True, progressive=True)
    print(f"wrote {POSTER.relative_to(ROOT)}")
    return paths


def encode_mp4(frames: list[Path]) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg not found — frames and poster are ready; skip MP4")
        return
    concat = OUT_DIR / "concat.txt"
    lines = []
    for frame in frames:
        lines.append(f"file '{frame}'")
        lines.append("duration 8")
    lines.append(f"file '{frames[-1]}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-vf",
        "fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-crf",
        "20",
        "-movflags",
        "+faststart",
        str(MP4),
    ]
    subprocess.run(cmd, check=True)
    concat.unlink(missing_ok=True)
    print(f"wrote {MP4.relative_to(ROOT)}")


def main() -> int:
    frames = render_frames()
    encode_mp4(frames)
    return 0


if __name__ == "__main__":
    sys.exit(main())
