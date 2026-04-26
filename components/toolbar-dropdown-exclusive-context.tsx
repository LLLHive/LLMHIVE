"use client"

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"

/**
 * Keys for mutually-exclusive toolbar menus in the chat header.
 * Desktop vs mobile use different keys so a hidden mobile `Sheet` cannot
 * accidentally mirror the same `open` state as a desktop `DropdownMenu`.
 */
export type ToolbarDropdownKey =
  | "powered-by"
  | "powered-by-mobile"
  | "industry"
  | "models"
  | "models-mobile"
  | "format"
  | "format-mobile"

type ToolbarDropdownExclusiveContextValue = {
  openKey: ToolbarDropdownKey | null
  /** Opening one menu closes any other; closing clears only if it matches. */
  setDropdownOpen: (key: ToolbarDropdownKey, open: boolean) => void
  isOpen: (key: ToolbarDropdownKey) => boolean
}

const ToolbarDropdownExclusiveContext =
  createContext<ToolbarDropdownExclusiveContextValue | null>(null)

export function ToolbarDropdownExclusiveProvider({ children }: { children: ReactNode }) {
  const [openKey, setOpenKey] = useState<ToolbarDropdownKey | null>(null)

  const setDropdownOpen = useCallback((key: ToolbarDropdownKey, open: boolean) => {
    setOpenKey((prev) => {
      if (!open) return prev === key ? null : prev
      return key
    })
  }, [])

  const isOpen = useCallback(
    (key: ToolbarDropdownKey) => openKey === key,
    [openKey],
  )

  const value = useMemo(
    () => ({ openKey, setDropdownOpen, isOpen }),
    [openKey, setDropdownOpen, isOpen],
  )

  return (
    <ToolbarDropdownExclusiveContext.Provider value={value}>
      {children}
    </ToolbarDropdownExclusiveContext.Provider>
  )
}

export function useToolbarDropdownExclusive(): ToolbarDropdownExclusiveContextValue {
  const ctx = useContext(ToolbarDropdownExclusiveContext)
  if (!ctx) {
    throw new Error(
      "useToolbarDropdownExclusive must be used within ToolbarDropdownExclusiveProvider",
    )
  }
  return ctx
}
