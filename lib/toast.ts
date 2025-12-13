// Toast notification system using sonner
// Sonner provides beautiful, accessible toast notifications

import { toast as sonnerToast } from 'sonner'

export const toast = {
  success: (message: string) => {
    sonnerToast.success(message, {
      duration: 3000,
    })
  },

  error: (message: string) => {
    sonnerToast.error(message, {
      duration: 5000,
    })
  },

  info: (message: string) => {
    sonnerToast.info(message, {
      duration: 3000,
    })
  },

  warning: (message: string) => {
    sonnerToast.warning(message, {
      duration: 4000,
    })
  },

  loading: (message: string) => {
    return sonnerToast.loading(message)
  },

  dismiss: (toastId?: string | number) => {
    sonnerToast.dismiss(toastId)
  },

  promise: <T>(
    promise: Promise<T>,
    messages: {
      loading: string
      success: string | ((data: T) => string)
      error: string | ((error: Error) => string)
    }
  ) => {
    return sonnerToast.promise(promise, messages)
  },
}
