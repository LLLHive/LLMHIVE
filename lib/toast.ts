import { toast as sonnerToast } from "sonner"

/**
 * Toast utility functions for LLMHive.
 * 
 * Provides consistent toast notifications across the application.
 * Uses sonner under the hood for a clean, modern toast experience.
 * 
 * Usage:
 * ```ts
 * import { toast } from "@/lib/toast"
 * 
 * toast.success("Settings saved!")
 * toast.error("Failed to load data")
 * toast.networkError()
 * toast.apiError(error)
 * ```
 */

export const toast = {
  /**
   * Show a success toast
   */
  success: (message: string, options?: { description?: string; duration?: number }) => {
    sonnerToast.success(message, {
      description: options?.description,
      duration: options?.duration ?? 4000,
    })
  },

  /**
   * Show an error toast
   */
  error: (message: string, options?: { description?: string; duration?: number }) => {
    sonnerToast.error(message, {
      description: options?.description,
      duration: options?.duration ?? 5000,
    })
  },

  /**
   * Show a warning toast
   */
  warning: (message: string, options?: { description?: string; duration?: number }) => {
    sonnerToast.warning(message, {
      description: options?.description,
      duration: options?.duration ?? 4000,
    })
  },

  /**
   * Show an info toast
   */
  info: (message: string, options?: { description?: string; duration?: number }) => {
    sonnerToast.info(message, {
      description: options?.description,
      duration: options?.duration ?? 4000,
    })
  },

  /**
   * Show a loading toast with promise
   */
  promise: <T,>(
    promise: Promise<T>,
    options: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((error: Error) => string)
    }
  ) => {
    return sonnerToast.promise(promise, options)
  },

  /**
   * Show a toast for network errors
   */
  networkError: (options?: { retry?: () => void }) => {
    sonnerToast.error("Connection Error", {
      description: "Unable to connect to the server. Please check your internet connection.",
      duration: 6000,
      action: options?.retry
        ? {
            label: "Retry",
            onClick: options.retry,
          }
        : undefined,
    })
  },

  /**
   * Show a toast for API errors
   */
  apiError: (error: { status?: number; message?: string }, options?: { retry?: () => void }) => {
    const status = error.status ?? 500
    let title = "Request Failed"
    let description = error.message ?? "Something went wrong. Please try again."

    if (status === 401) {
      title = "Authentication Required"
      description = "Please sign in to continue."
    } else if (status === 403) {
      title = "Access Denied"
      description = "You don't have permission to perform this action."
    } else if (status === 404) {
      title = "Not Found"
      description = "The requested resource could not be found."
    } else if (status === 429) {
      title = "Too Many Requests"
      description = "Please slow down and try again later."
    } else if (status >= 500) {
      title = "Server Error"
      description = "The server encountered an error. Please try again later."
    }

    sonnerToast.error(title, {
      description,
      duration: 5000,
      action: options?.retry
        ? {
            label: "Retry",
            onClick: options.retry,
          }
        : undefined,
    })
  },

  /**
   * Show a toast for timeout errors
   */
  timeout: (options?: { retry?: () => void }) => {
    sonnerToast.error("Request Timeout", {
      description: "The request took too long to complete. Please try again.",
      duration: 5000,
      action: options?.retry
        ? {
            label: "Retry",
            onClick: options.retry,
          }
        : undefined,
    })
  },

  /**
   * Show a toast for retry status
   */
  retrying: (attempt: number, maxAttempts: number) => {
    sonnerToast.info(`Retrying...`, {
      description: `Attempt ${attempt} of ${maxAttempts}`,
      duration: 2000,
    })
  },

  /**
   * Show a toast for settings saved
   */
  settingsSaved: () => {
    sonnerToast.success("Settings Saved", {
      description: "Your preferences have been updated.",
      duration: 3000,
    })
  },

  /**
   * Show a toast for settings error
   */
  settingsError: () => {
    sonnerToast.error("Failed to Save", {
      description: "Could not save your settings. Please try again.",
      duration: 5000,
    })
  },

  /**
   * Show a toast for copy action
   */
  copied: (what: string = "Content") => {
    sonnerToast.success(`${what} Copied`, {
      description: "Copied to clipboard.",
      duration: 2000,
    })
  },

  /**
   * Dismiss all toasts
   */
  dismiss: () => {
    sonnerToast.dismiss()
  },

  /**
   * Custom toast with full control
   */
  custom: sonnerToast,
}

export default toast
