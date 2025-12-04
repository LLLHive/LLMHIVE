"use client"

import React, { Component, type ErrorInfo, type ReactNode } from "react"
import { AlertTriangle, RefreshCw, Bug, Copy, Check } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
  errorId: string
  copied: boolean
}

/**
 * Error Boundary component that catches React errors and displays a user-friendly error message.
 * 
 * Usage:
 * ```tsx
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 * 
 * // With custom fallback
 * <ErrorBoundary fallback={<CustomErrorUI />}>
 *   <YourComponent />
 * </ErrorBoundary>
 * 
 * // With error callback
 * <ErrorBoundary onError={(error, info) => logToService(error, info)}>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    errorId: "",
    copied: false,
  }

  private generateErrorId(): string {
    return `ERR-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).substr(2, 4).toUpperCase()}`
  }

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const errorId = this.generateErrorId()
    
    // Log error to console with full details
    console.group(`[ErrorBoundary] Error caught - ${errorId}`)
    console.error("Error:", error)
    console.error("Error message:", error.message)
    console.error("Error stack:", error.stack)
    console.error("Component stack:", errorInfo.componentStack)
    console.groupEnd()

    this.setState({
      errorInfo,
      errorId,
    })

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo)
  }

  private handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: "",
      copied: false,
    })
  }

  private handleCopyErrorDetails = async (): Promise<void> => {
    const { error, errorInfo, errorId } = this.state
    
    const errorDetails = `
Error ID: ${errorId}
Timestamp: ${new Date().toISOString()}
Error: ${error?.message || "Unknown error"}
Stack: ${error?.stack || "No stack trace"}
Component Stack: ${errorInfo?.componentStack || "No component stack"}
User Agent: ${typeof navigator !== "undefined" ? navigator.userAgent : "Unknown"}
URL: ${typeof window !== "undefined" ? window.location.href : "Unknown"}
    `.trim()

    try {
      await navigator.clipboard.writeText(errorDetails)
      this.setState({ copied: true })
      setTimeout(() => this.setState({ copied: false }), 2000)
    } catch (err) {
      console.error("Failed to copy error details:", err)
    }
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      const { error, errorId, copied } = this.state

      return (
        <div className="min-h-[400px] flex items-center justify-center p-6 bg-background/50 rounded-lg border border-destructive/20">
          <div className="max-w-md w-full text-center space-y-6">
            {/* Error Icon */}
            <div className="flex justify-center">
              <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center animate-pulse">
                <AlertTriangle className="h-8 w-8 text-destructive" />
              </div>
            </div>

            {/* Error Message */}
            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-foreground">
                Something went wrong
              </h2>
              <p className="text-sm text-muted-foreground">
                {error?.message || "An unexpected error occurred in this component."}
              </p>
            </div>

            {/* Error ID */}
            {errorId && (
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted/50 border border-border">
                <Bug className="h-3.5 w-3.5 text-muted-foreground" />
                <code className="text-xs text-muted-foreground font-mono">
                  {errorId}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 -mr-1"
                  onClick={this.handleCopyErrorDetails}
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-green-500" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                </Button>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button
                onClick={this.handleReset}
                variant="default"
                className="gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Try Again
              </Button>
              <Button
                onClick={() => window.location.reload()}
                variant="outline"
                className="gap-2"
              >
                Reload Page
              </Button>
            </div>

            {/* Help Text */}
            <p className="text-xs text-muted-foreground">
              If this keeps happening, please copy the error details and contact support.
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * Hook-style error boundary wrapper for functional components.
 * 
 * Usage:
 * ```tsx
 * function MyComponent() {
 *   return (
 *     <WithErrorBoundary>
 *       <ComponentThatMightError />
 *     </WithErrorBoundary>
 *   )
 * }
 * ```
 */
export function WithErrorBoundary({
  children,
  fallback,
  onError,
}: Props): React.ReactElement {
  return (
    <ErrorBoundary fallback={fallback} onError={onError}>
      {children}
    </ErrorBoundary>
  )
}

export default ErrorBoundary
