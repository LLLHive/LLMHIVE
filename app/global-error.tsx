"use client"

import { useEffect, useState } from "react"
import { AlertOctagon, RefreshCw, Home, Copy, Check, Bug } from "lucide-react"
import * as Sentry from "@sentry/nextjs"

/**
 * Global error handler for root layout errors.
 * 
 * This catches errors that occur in the root layout itself,
 * which the regular error.tsx cannot catch.
 * 
 * Note: This must include its own <html> and <body> tags
 * since it replaces the entire root layout.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const [errorId, setErrorId] = useState<string>("")
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const id = `GLOBAL-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).substr(2, 4).toUpperCase()}`
    setErrorId(error.digest || id)
    
    // Report to Sentry
    Sentry.captureException(error, {
      tags: {
        error_type: "global_error",
        error_id: error.digest || id,
      },
      extra: {
        url: typeof window !== "undefined" ? window.location.href : "unknown",
      },
    })
    
    console.group(`[Global Error] ${id}`)
    console.error("Error:", error)
    console.error("Message:", error.message)
    console.error("Stack:", error.stack)
    console.groupEnd()
  }, [error])

  const handleCopyError = async () => {
    const errorDetails = `
Error ID: ${errorId}
Timestamp: ${new Date().toISOString()}
Message: ${error.message || "Unknown error"}
Stack: ${error.stack || "No stack trace available"}
URL: ${typeof window !== "undefined" ? window.location.href : "Unknown"}
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
    <html lang="en" className="dark">
      <body className="font-sans antialiased bg-background text-foreground">
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="max-w-lg w-full text-center space-y-6">
            {/* Critical Error Icon */}
            <div className="flex justify-center">
              <div className="w-24 h-24 rounded-full bg-red-500/20 flex items-center justify-center">
                <AlertOctagon className="h-12 w-12 text-red-500 animate-pulse" />
              </div>
            </div>
            
            {/* Error Message */}
            <div className="space-y-3">
              <h1 className="text-3xl font-bold text-foreground">
                Critical Error
              </h1>
              <p className="text-lg text-muted-foreground">
                A critical error has occurred that prevented the application from loading.
              </p>
              <p className="text-sm text-muted-foreground/80">
                {error.message || "Please try refreshing the page."}
              </p>
            </div>

            {/* Error ID */}
            <div className="flex justify-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
                <Bug className="h-4 w-4 text-red-400" />
                <span className="text-sm text-muted-foreground">Error ID:</span>
                <code className="text-sm font-mono text-foreground font-medium">
                  {errorId}
                </code>
                <button
                  className="p-1 hover:bg-red-500/10 rounded transition-colors"
                  onClick={handleCopyError}
                  title="Copy error details"
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
              <button
                onClick={reset}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-gradient-to-r from-amber-600 to-yellow-500 text-white font-medium hover:opacity-90 transition-opacity"
              >
                <RefreshCw className="h-4 w-4" />
                Try Again
              </button>
              <a
                href="/"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg border border-border bg-background hover:bg-muted transition-colors font-medium"
              >
                <Home className="h-4 w-4" />
                Return Home
              </a>
            </div>

            {/* Help */}
            <p className="text-xs text-muted-foreground pt-4">
              If this problem persists, please clear your browser cache or contact support with the Error ID.
            </p>
          </div>
        </div>

        {/* Inline styles for when CSS might not load */}
        <style>{`
          :root {
            --background: 20 14.3% 4.1%;
            --foreground: 60 9.1% 97.8%;
            --muted-foreground: 24 5.4% 63.9%;
            --border: 12 6.5% 15.1%;
          }
          .bg-background { background-color: hsl(var(--background)); }
          .text-foreground { color: hsl(var(--foreground)); }
          .text-muted-foreground { color: hsl(var(--muted-foreground)); }
          .border-border { border-color: hsl(var(--border)); }
        `}</style>
      </body>
    </html>
  )
}
