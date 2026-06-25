import Link from "next/link"
import { cn } from "@/lib/utils"
import { ENTERPRISE_SINGLE_FLAGSHIP_PICK_LABEL } from "@/lib/billing/enterprise-features"

type EnterpriseFlagshipPickHintProps = {
  className?: string
  /** When true, render as inline muted text; when false, slightly more prominent. */
  subtle?: boolean
}

export function EnterpriseFlagshipPickHint({
  className,
  subtle = true,
}: EnterpriseFlagshipPickHintProps) {
  return (
    <p
      className={cn(
        subtle ? "text-[10px] sm:text-xs text-muted-foreground" : "text-xs text-zinc-300",
        className,
      )}
    >
      <Link
        href="/pricing"
        className="underline underline-offset-2 hover:text-[var(--bronze)] transition-colors"
      >
        {ENTERPRISE_SINGLE_FLAGSHIP_PICK_LABEL}
      </Link>
    </p>
  )
}
