"use client";

import LogoText from "./LogoText";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  /** Page title displayed after the LLMHive logo */
  title: string;
  /** Optional subtitle/description */
  subtitle?: string;
  /** Additional CSS classes for the container */
  className?: string;
  /** Size variant */
  size?: "default" | "large" | "compact";
}

/**
 * Consistent page header with LLMHive branding.
 * Use this at the top of every internal page for brand consistency.
 */
export function PageHeader({ 
  title, 
  subtitle, 
  className,
  size = "default" 
}: PageHeaderProps) {
  const logoHeight = size === "large" ? 52 : size === "compact" ? 32 : 42;
  const titleSize = size === "large" ? "text-4xl" : size === "compact" ? "text-xl" : "text-2xl";
  
  return (
    <div className={cn("flex flex-col gap-2 mb-6", className)}>
      <div className="flex items-center gap-4">
        <LogoText height={logoHeight} />
        
        {/* Decorative divider with gold gradient */}
        <div className="h-8 w-px bg-gradient-to-b from-transparent via-amber-500/50 to-transparent" />
        
        <h1 className={cn(
          titleSize,
          "font-semibold text-white tracking-wide"
        )}>
          {title}
        </h1>
      </div>
      
      {subtitle && (
        <p className="text-white/60 text-sm ml-1 pl-2 border-l border-amber-500/20">
          {subtitle}
        </p>
      )}
    </div>
  );
}

export default PageHeader;

