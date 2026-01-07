"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { AlertTriangle, RefreshCw, Home, Copy, Check, Bug, ChevronDown, ChevronUp } from "lucide-react"
import Link from "next/link"
import * as Sentry from "@sentry/nextjs"

/**
 * Global error page for Next.js App Router.
 * 
 * This component is automatically rendered when an error occurs
 * in any server component or during server-side rendering.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const [errorId, setErrorId] = useState<string>("")
  const [copied, setCopied] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    // Generate error ID for support reference
    const id = `ERR-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).substr(2, 4).toUpperCase()}`
    setErrorId(error.digest || id)
    
    // Report to Sentry
    Sentry.captureException(error, {
      tags: {
        error_type: "app_error",
        error_id: error.digest || id,
      },
      extra: {
        url: typeof window !== "undefined" ? window.location.href : "unknown",
        userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
      },
    })
    
    // Log the error to console with full details
    console.group(`[App Error] ${id}`)
    console.error("Error:", error)
    console.error("Message:", error.message)
    console.error("Stack:", error.stack)
    console.error("Digest:", error.digest)
    console.error("Timestamp:", new Date().toISOString())
    console.groupEnd()
  }, [error])

  const handleCopyError = async () => {
    const errorDetails = `
Error ID: ${errorId}
Timestamp: ${new Date().toISOString()}
Message: ${error.message || "Unknown error"}
Stack: ${error.stack || "No stack trace available"}
URL: ${typeof window !== "undefined" ? window.location.href : "Unknown"}
User Agent: ${typeof navigator !== "undefined" ? navigator.userAgent : "Unknown"}
    `.trim()

    try {
      await navigator.clipboard.writeText(errorDetails)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error("Failed to copy:", err)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      {/* Background pattern */}
      <div
        className="fixed inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 0l25.98 15v30L30 60 4.02 45V15z' fill='none' stroke='%23C48E48' strokeWidth='1'/%3E%3C/svg%3E")`,
          backgroundSize: "60px 60px",
        }}
      />
      
      <div className="max-w-lg w-full text-center space-y-6 relative z-10">
        {/* Error Icon with animation */}
        <div className="flex justify-center">
          <div className="w-20 h-20 rounded-full bg-destructive/10 flex items-center justify-center animate-pulse">
            <AlertTriangle className="h-10 w-10 text-destructive" />
          </div>
        </div>
        
        {/* Error Message */}
        <div className="space-y-3">
          <h1 className="text-3xl font-bold text-foreground">
            Something went wrong
          </h1>
          <p className="text-muted-foreground text-lg">
            We apologize for the inconvenience. An unexpected error has occurred.
          </p>
          <p className="text-sm text-muted-foreground/80">
            {error.message || "Please try again or return to the home page."}
          </p>
        </div>

        {/* Error ID Badge */}
        <div className="flex justify-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-muted/50 border border-border">
            <Bug className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Error ID:</span>
            <code className="text-sm font-mono text-foreground font-medium">
              {errorId}
            </code>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 -mr-1"
              onClick={handleCopyError}
              title="Copy error details"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Button 
            onClick={reset} 
            variant="default" 
            size="lg"
            className="gap-2 bronze-gradient"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
          <Link href="/">
            <Button variant="outline" size="lg" className="gap-2 w-full sm:w-auto">
              <Home className="h-4 w-4" />
              Return Home
            </Button>
          </Link>
        </div>

        {/* Technical Details (Collapsible) */}
        {error.stack && (
          <div className="pt-4">
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground gap-1"
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? (
                <>
                  <ChevronUp className="h-3 w-3" />
                  Hide Technical Details
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3" />
                  Show Technical Details
                </>
              )}
            </Button>
            
            {showDetails && (
              <div className="mt-3 p-4 rounded-lg bg-muted/30 border border-border text-left overflow-auto max-h-48">
                <pre className="text-xs text-muted-foreground font-mono whitespace-pre-wrap break-words">
                  {error.stack}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Help Text */}
        <p className="text-xs text-muted-foreground pt-4">
          If this problem persists, please contact support with the Error ID above.
        </p>
      </div>
    </div>
  )
}
