import { cn } from "@/lib/utils";

interface LogoTextProps {
  /** Height in pixels - controls font size proportionally */
  height?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * LLMHive logo text with 3D metallic gold styling.
 * Designed to match the look and feel of the 3D rendered gold logo.
 */
export default function LogoText({ height = 48, className = "" }: LogoTextProps) {
  // Convert height to appropriate font size (roughly 65% of height for visual balance)
  const fontSize = Math.round(height * 0.65);
  
  // Use smaller, less dramatic style for compact displays
  const isSmall = height < 40;

  return (
    <span
      className={cn(
        isSmall ? "llmhive-logo-text-sm" : "llmhive-logo-text",
        "select-none whitespace-nowrap",
        className
      )}
      style={{ fontSize: `${fontSize}px` }}
    >
      LLMHive
    </span>
  );
}
