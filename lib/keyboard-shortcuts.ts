/**
 * Keyboard Shortcuts Manager for LLMHive
 * 
 * Provides global keyboard shortcuts for common actions
 */

export interface KeyboardShortcut {
  key: string
  modifiers: {
    ctrl?: boolean
    alt?: boolean
    shift?: boolean
    meta?: boolean
  }
  description: string
  action: () => void
}

export interface ShortcutContext {
  id: string
  shortcuts: KeyboardShortcut[]
}

class KeyboardShortcutsManager {
  private contexts: Map<string, ShortcutContext> = new Map()
  private activeContexts: Set<string> = new Set()
  private isEnabled: boolean = true

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', this.handleKeyDown.bind(this))
    }
  }

  private handleKeyDown(event: KeyboardEvent): void {
    if (!this.isEnabled) return

    // Don't trigger shortcuts when typing in inputs
    const target = event.target as HTMLElement
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      // Allow specific shortcuts even in inputs
      const isEscape = event.key === 'Escape'
      const isNewChat = event.key === 'n' && (event.metaKey || event.ctrlKey) && event.shiftKey
      const isSend = event.key === 'Enter' && (event.metaKey || event.ctrlKey)
      
      if (!isEscape && !isNewChat && !isSend) {
        return
      }
    }

    // Check each active context for matching shortcuts
    for (const contextId of this.activeContexts) {
      const context = this.contexts.get(contextId)
      if (!context) continue

      for (const shortcut of context.shortcuts) {
        if (this.matchesShortcut(event, shortcut)) {
          event.preventDefault()
          event.stopPropagation()
          shortcut.action()
          return
        }
      }
    }
  }

  private matchesShortcut(event: KeyboardEvent, shortcut: KeyboardShortcut): boolean {
    const keyMatches = event.key.toLowerCase() === shortcut.key.toLowerCase()
    const ctrlMatches = !!shortcut.modifiers.ctrl === (event.ctrlKey || event.metaKey)
    const altMatches = !!shortcut.modifiers.alt === event.altKey
    const shiftMatches = !!shortcut.modifiers.shift === event.shiftKey
    
    return keyMatches && ctrlMatches && altMatches && shiftMatches
  }

  public registerContext(context: ShortcutContext): void {
    this.contexts.set(context.id, context)
    this.activeContexts.add(context.id)
  }

  public unregisterContext(contextId: string): void {
    this.contexts.delete(contextId)
    this.activeContexts.delete(contextId)
  }

  public activateContext(contextId: string): void {
    this.activeContexts.add(contextId)
  }

  public deactivateContext(contextId: string): void {
    this.activeContexts.delete(contextId)
  }

  public enable(): void {
    this.isEnabled = true
  }

  public disable(): void {
    this.isEnabled = false
  }

  public getActiveShortcuts(): KeyboardShortcut[] {
    const shortcuts: KeyboardShortcut[] = []
    for (const contextId of this.activeContexts) {
      const context = this.contexts.get(contextId)
      if (context) {
        shortcuts.push(...context.shortcuts)
      }
    }
    return shortcuts
  }

  public formatShortcut(shortcut: KeyboardShortcut): string {
    const parts: string[] = []
    const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0
    
    if (shortcut.modifiers.ctrl) {
      parts.push(isMac ? '⌘' : 'Ctrl')
    }
    if (shortcut.modifiers.alt) {
      parts.push(isMac ? '⌥' : 'Alt')
    }
    if (shortcut.modifiers.shift) {
      parts.push(isMac ? '⇧' : 'Shift')
    }
    
    // Format the key
    let key = shortcut.key.toUpperCase()
    if (key === 'ENTER') key = '↵'
    if (key === 'ESCAPE') key = 'Esc'
    if (key === 'ARROWUP') key = '↑'
    if (key === 'ARROWDOWN') key = '↓'
    if (key === 'ARROWLEFT') key = '←'
    if (key === 'ARROWRIGHT') key = '→'
    
    parts.push(key)
    
    return parts.join(isMac ? '' : '+')
  }
}

// Singleton instance
export const keyboardShortcuts = new KeyboardShortcutsManager()

// Default chat shortcuts
export const CHAT_SHORTCUTS: ShortcutContext = {
  id: 'chat',
  shortcuts: [
    {
      key: 'n',
      modifiers: { ctrl: true, shift: true },
      description: 'New chat',
      action: () => {
        // This will be overridden when registered
        document.dispatchEvent(new CustomEvent('llmhive:newChat'))
      },
    },
    {
      key: 'k',
      modifiers: { ctrl: true },
      description: 'Focus search',
      action: () => {
        document.dispatchEvent(new CustomEvent('llmhive:focusSearch'))
      },
    },
    {
      key: 'Escape',
      modifiers: {},
      description: 'Close modal / Cancel',
      action: () => {
        document.dispatchEvent(new CustomEvent('llmhive:escape'))
      },
    },
    {
      key: '/',
      modifiers: { ctrl: true },
      description: 'Show shortcuts',
      action: () => {
        document.dispatchEvent(new CustomEvent('llmhive:showShortcuts'))
      },
    },
    {
      key: 's',
      modifiers: { ctrl: true },
      description: 'Save settings',
      action: () => {
        document.dispatchEvent(new CustomEvent('llmhive:saveSettings'))
      },
    },
  ],
}

/**
 * React hook-friendly shortcut registration
 */
export function useKeyboardShortcuts() {
  return {
    register: (context: ShortcutContext) => keyboardShortcuts.registerContext(context),
    unregister: (contextId: string) => keyboardShortcuts.unregisterContext(contextId),
    getActiveShortcuts: () => keyboardShortcuts.getActiveShortcuts(),
    formatShortcut: (shortcut: KeyboardShortcut) => keyboardShortcuts.formatShortcut(shortcut),
  }
}

