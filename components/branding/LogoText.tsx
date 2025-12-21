"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";

interface LogoTextProps {
  /** Height in pixels - controls the wordmark size */
  height?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * LLMHive wordmark image component.
 * Uses the 3D metallic rendered wordmark image.
 */
export default function LogoText({ height = 48, className = "" }: LogoTextProps) {
  // The source image aspect ratio (approximately 4.5:1 based on the logo)
  const aspectRatio = 4.5;
  const width = Math.round(height * aspectRatio);

  return (
    <Image
      src="/llmhive/logo-text.png"
      alt="LLMHive"
      width={width}
      height={height}
      className={cn("select-none object-contain", className)}
      priority
      unoptimized
    />
  );
}
