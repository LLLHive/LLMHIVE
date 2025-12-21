import Image from "next/image";
import { cn } from "@/lib/utils";

type LogoVariant = "nav" | "title" | "hero";

interface LogoTextProps {
  /** Height in pixels - controls image height */
  height?: number;
  /** Additional CSS classes */
  className?: string;
  /** Variant determines which wordmark image to use */
  variant?: LogoVariant;
}

// Image paths for each variant
const WORDMARK_IMAGES: Record<LogoVariant, string> = {
  nav: "/llmhive/llmhive-wordmark-nav.png",
  title: "/llmhive/llmhive-wordmark-title.png",
  hero: "/llmhive/llmhive-wordmark-hero.png",
};

// Aspect ratios for each image (width/height) - adjust based on actual images
const ASPECT_RATIOS: Record<LogoVariant, number> = {
  nav: 3.5,    // Nav wordmark is wider
  title: 3.5,  // Title wordmark
  hero: 3.5,   // Hero wordmark
};

/**
 * LLMHive wordmark using image assets with transparent backgrounds.
 * Uses different image variants optimized for nav, title, and hero contexts.
 */
export default function LogoText({ 
  height = 48, 
  className = "",
  variant,
}: LogoTextProps) {
  // Auto-detect variant based on height if not specified
  const resolvedVariant: LogoVariant = variant ?? (height <= 32 ? "nav" : height >= 56 ? "hero" : "title");
  
  const imageSrc = WORDMARK_IMAGES[resolvedVariant];
  const aspectRatio = ASPECT_RATIOS[resolvedVariant];
  const width = Math.round(height * aspectRatio);

  return (
    <Image
      src={imageSrc}
      alt="LLMHive"
      width={width}
      height={height}
      className={cn("select-none object-contain", className)}
      priority={resolvedVariant === "hero"}
    />
  );
}
