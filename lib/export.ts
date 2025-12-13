/**
 * Export Utility for LLMHive
 * 
 * Provides various export formats for conversations:
 * - Markdown
 * - Plain text
 * - JSON
 * - PDF (via print)
 * - Clipboard
 */

import type { Conversation, Message } from './types'

export type ExportFormat = 'markdown' | 'text' | 'json' | 'html'

export interface ExportOptions {
  format: ExportFormat
  includeMetadata?: boolean
  includeTimestamps?: boolean
  includeModels?: boolean
}

/**
 * Format a single message
 */
function formatMessage(message: Message, options: ExportOptions): string {
  const role = message.role === 'user' ? 'You' : 'Assistant'
  const timestamp = options.includeTimestamps && message.timestamp
    ? new Date(message.timestamp).toLocaleString()
    : ''
  const models = options.includeModels && message.model
    ? ` (${message.model})`
    : ''
  
  switch (options.format) {
    case 'markdown':
      return `### ${role}${models}\n${timestamp ? `*${timestamp}*\n\n` : '\n'}${message.content}\n`
    case 'text':
      return `${role}${models}${timestamp ? ` [${timestamp}]` : ''}:\n${message.content}\n\n`
    case 'json':
      return JSON.stringify({
        role: message.role,
        content: message.content,
        timestamp: message.timestamp,
        model: message.model,
      }, null, 2)
    case 'html':
      return `<div class="message ${message.role}">
        <div class="message-header">
          <strong>${role}</strong>${models}
          ${timestamp ? `<span class="timestamp">${timestamp}</span>` : ''}
        </div>
        <div class="message-content">${escapeHtml(message.content)}</div>
      </div>`
    default:
      return message.content
  }
}

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML.replace(/\n/g, '<br>')
}

/**
 * Export a conversation to the specified format
 */
export function exportConversation(
  conversation: Conversation,
  options: ExportOptions = { format: 'markdown' }
): string {
  const { format, includeMetadata = true } = options
  
  let output = ''
  
  // Add header
  switch (format) {
    case 'markdown':
      output += `# ${conversation.title}\n\n`
      if (includeMetadata) {
        output += `**Created:** ${new Date(conversation.createdAt).toLocaleString()}\n`
        output += `**Model:** ${conversation.model || 'Multiple'}\n\n`
        output += '---\n\n'
      }
      break
    case 'text':
      output += `${conversation.title}\n${'='.repeat(conversation.title.length)}\n\n`
      if (includeMetadata) {
        output += `Created: ${new Date(conversation.createdAt).toLocaleString()}\n`
        output += `Model: ${conversation.model || 'Multiple'}\n\n`
      }
      break
    case 'json':
      return JSON.stringify({
        id: conversation.id,
        title: conversation.title,
        createdAt: conversation.createdAt,
        updatedAt: conversation.updatedAt,
        model: conversation.model,
        messages: conversation.messages,
      }, null, 2)
    case 'html':
      output += `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(conversation.title)}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #1a1a1a; color: #e5e5e5; }
    h1 { color: #cd7f32; border-bottom: 2px solid #cd7f32; padding-bottom: 10px; }
    .message { margin: 20px 0; padding: 15px; border-radius: 10px; }
    .message.user { background: #2a2a2a; border-left: 3px solid #cd7f32; }
    .message.assistant { background: #1e1e1e; border-left: 3px solid #4a9eff; }
    .message-header { font-size: 0.9em; margin-bottom: 10px; color: #888; }
    .message-header strong { color: #e5e5e5; }
    .timestamp { float: right; font-size: 0.85em; }
    .metadata { color: #888; font-size: 0.9em; margin-bottom: 20px; }
  </style>
</head>
<body>
  <h1>${escapeHtml(conversation.title)}</h1>
  ${includeMetadata ? `<div class="metadata">
    <p>Created: ${new Date(conversation.createdAt).toLocaleString()}</p>
    <p>Model: ${conversation.model || 'Multiple'}</p>
  </div>` : ''}`
      break
  }
  
  // Add messages
  for (const message of conversation.messages) {
    output += formatMessage(message, options)
  }
  
  // Close HTML
  if (format === 'html') {
    output += '</body></html>'
  }
  
  return output
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }
}

/**
 * Download conversation as a file
 */
export function downloadConversation(
  conversation: Conversation,
  options: ExportOptions = { format: 'markdown' }
): void {
  const content = exportConversation(conversation, options)
  
  const mimeTypes: Record<ExportFormat, string> = {
    markdown: 'text/markdown',
    text: 'text/plain',
    json: 'application/json',
    html: 'text/html',
  }
  
  const extensions: Record<ExportFormat, string> = {
    markdown: 'md',
    text: 'txt',
    json: 'json',
    html: 'html',
  }
  
  const blob = new Blob([content], { type: mimeTypes[options.format] })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = `${sanitizeFilename(conversation.title)}.${extensions[options.format]}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
}

function sanitizeFilename(name: string): string {
  return name
    .replace(/[^a-z0-9\s-]/gi, '')
    .replace(/\s+/g, '-')
    .toLowerCase()
    .slice(0, 100)
}

/**
 * Share conversation (using Web Share API if available)
 */
export async function shareConversation(
  conversation: Conversation,
  options: ExportOptions = { format: 'text' }
): Promise<boolean> {
  const content = exportConversation(conversation, options)
  
  // Try native share first
  if (navigator.share) {
    try {
      await navigator.share({
        title: conversation.title,
        text: content,
      })
      return true
    } catch (error) {
      // User cancelled or share failed, fall back to clipboard
      if ((error as Error).name !== 'AbortError') {
        console.error('Share failed:', error)
      }
    }
  }
  
  // Fall back to clipboard
  return copyToClipboard(content)
}

/**
 * Export a single message
 */
export function exportMessage(message: Message, format: ExportFormat = 'text'): string {
  return formatMessage(message, { format, includeTimestamps: true, includeModels: true })
}

/**
 * Copy a single message to clipboard
 */
export async function copyMessage(message: Message): Promise<boolean> {
  return copyToClipboard(message.content)
}

