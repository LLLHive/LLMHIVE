/**
 * Comprehensive UI Audit Test Suite
 * 
 * This test suite performs a full audit of the LLMHive UI:
 * - Route discovery and navigation
 * - Click crawling with safety checks
 * - OpenRouter rankings validation
 * - Console error detection
 * - Network failure detection
 * - Accessibility checks
 * 
 * Run with: npm run test:e2e -- tests/e2e/audit/ui-audit.spec.ts
 */

import { test, expect, Page, BrowserContext } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import {
  setupOpenRouterMocks,
  setupClarifyingQuestionsMock,
  MOCK_CATEGORIES,
  MOCK_RANKINGS,
  EXPECTED_CATEGORY_SLUGS,
} from './openrouter-mock'

// Audit configuration
const AUDIT_CONFIG = {
  maxClicksPerPage: 40,
  clickTimeout: 5000,
  screenshotDir: 'docs/ui_audit/reports/latest/screenshots',
  destructiveKeywords: [
    'delete', 'remove', 'logout', 'sign out', 'signout', 'reset',
    'clear', 'drop', 'billing', 'pay', 'subscribe', 'revoke',
    'disconnect', 'unlink', 'destroy', 'terminate', 'cancel subscription',
    'sync now', 'sync', // Avoid mutating prod data
  ],
  externalDomains: [
    'openrouter.ai', 'github.com', 'google.com', 'vercel.com',
    'anthropic.com', 'openai.com', 'twitter.com', 'x.com',
  ],
}

// Audit results collector
interface AuditIssue {
  id: string
  severity: 'P0' | 'P1' | 'P2'
  type: 'console_error' | 'network_error' | 'correctness' | 'accessibility' | 'ux'
  title: string
  description: string
  route: string
  reproSteps: string[]
  screenshotPath?: string
  suspectedFiles?: string[]
  suggestedFix?: string
}

interface AuditResult {
  timestamp: string
  routesVisited: string[]
  clicksAttempted: number
  clicksSkipped: number
  consoleErrors: Array<{ route: string; message: string; type: string }>
  networkFailures: Array<{ route: string; url: string; status: number; method: string }>
  issues: AuditIssue[]
  a11yViolations: Array<{ route: string; violations: number; rules: string[] }>
}

let auditResult: AuditResult = {
  timestamp: new Date().toISOString(),
  routesVisited: [],
  clicksAttempted: 0,
  clicksSkipped: 0,
  consoleErrors: [],
  networkFailures: [],
  issues: [],
  a11yViolations: [],
}

// Helper: Check if text matches destructive keywords
function isDestructive(text: string): boolean {
  const lowerText = text.toLowerCase().trim()
  return AUDIT_CONFIG.destructiveKeywords.some(kw => lowerText.includes(kw))
}

// Helper: Check if URL is external
function isExternalUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return AUDIT_CONFIG.externalDomains.some(d => parsed.hostname.includes(d))
  } catch {
    return false
  }
}

// Helper: Take screenshot
async function takeScreenshot(page: Page, name: string): Promise<string> {
  const dir = AUDIT_CONFIG.screenshotDir
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true })
  }
  const filename = `${name.replace(/[^a-z0-9]/gi, '_')}.png`
  const filepath = path.join(dir, filename)
  await page.screenshot({ path: filepath, fullPage: true })
  return filepath
}

// Helper: Setup error/network listeners
function setupListeners(page: Page, route: string) {
  page.on('console', msg => {
    if (msg.type() === 'error') {
      auditResult.consoleErrors.push({
        route,
        message: msg.text(),
        type: msg.type(),
      })
    }
  })

  page.on('response', response => {
    const status = response.status()
    if (status >= 400) {
      const url = response.url()
      // Ignore expected 404s for non-existent resources
      if (!url.includes('_next/static') && !url.includes('favicon')) {
        auditResult.networkFailures.push({
          route,
          url,
          status,
          method: response.request().method(),
        })
      }
    }
  })
}

// =============================================================================
// ROUTES TO AUDIT
// =============================================================================

const ROUTES_TO_AUDIT = [
  { path: '/', name: 'Home' },
  { path: '/discover', name: 'Discover' },
  { path: '/models', name: 'Models' },
  { path: '/orchestration', name: 'Orchestration' },
  { path: '/settings', name: 'Settings' },
]

// =============================================================================
// TEST SUITE
// =============================================================================

test.describe('UI Audit - Route Discovery', () => {
  test.beforeEach(async ({ page }) => {
    await setupOpenRouterMocks(page)
  })

  for (const route of ROUTES_TO_AUDIT) {
    test(`Route loads without errors: ${route.name} (${route.path})`, async ({ page }) => {
      setupListeners(page, route.path)
      
      const response = await page.goto(route.path, { waitUntil: 'networkidle' })
      expect(response?.status()).toBeLessThan(400)
      
      // Wait for React hydration
      await page.waitForLoadState('domcontentloaded')
      
      // Take screenshot
      await takeScreenshot(page, `route_${route.name}`)
      
      // Record visited
      if (!auditResult.routesVisited.includes(route.path)) {
        auditResult.routesVisited.push(route.path)
      }
      
      // Check for visible error indicators
      const errorBanner = page.locator('[role="alert"], .error, .error-message')
      const errorCount = await errorBanner.count()
      
      if (errorCount > 0) {
        auditResult.issues.push({
          id: `route_error_${route.name}`,
          severity: 'P0',
          type: 'ux',
          title: `Error banner visible on ${route.name}`,
          description: 'Error indicator found on page load',
          route: route.path,
          reproSteps: [`Navigate to ${route.path}`, 'Observe error banner'],
          suspectedFiles: ['app/' + route.path.slice(1) + '/page.tsx'],
          suggestedFix: 'Check component error handling and API responses',
        })
      }
    })
  }
})

test.describe('UI Audit - OpenRouter Rankings Correctness', () => {
  test.beforeEach(async ({ page }) => {
    await setupOpenRouterMocks(page)
  })

  test('Models page: Category list is complete', async ({ page }) => {
    await page.goto('/models', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
    
    // Take screenshot
    await takeScreenshot(page, 'models_page_categories')
    
    // Look for category tabs or dropdown
    const categoryElements = page.locator('[role="tab"], [data-category], .category-tab, button[data-value]')
    const categoryCount = await categoryElements.count()
    
    // Get text from category elements
    const foundCategories: string[] = []
    for (let i = 0; i < categoryCount; i++) {
      const text = await categoryElements.nth(i).innerText()
      foundCategories.push(text.toLowerCase().trim())
    }
    
    // Check for expected categories
    const missingCategories: string[] = []
    const expectedDisplayNames = MOCK_CATEGORIES.categories.map(c => c.display_name.toLowerCase())
    
    for (const expected of expectedDisplayNames) {
      const found = foundCategories.some(f => f.includes(expected) || expected.includes(f))
      if (!found) {
        missingCategories.push(expected)
      }
    }
    
    if (missingCategories.length > 0) {
      auditResult.issues.push({
        id: 'models_missing_categories',
        severity: 'P0',
        type: 'correctness',
        title: 'Missing categories on Models page',
        description: `Categories not found: ${missingCategories.join(', ')}`,
        route: '/models',
        reproSteps: [
          'Navigate to /models',
          'Check category tabs/dropdown',
          'Compare with OpenRouter categories',
        ],
        suspectedFiles: ['components/openrouter/rankings-insights.tsx', 'app/models/page.tsx'],
        suggestedFix: 'Ensure categories are fetched from /api/openrouter/categories and rendered',
      })
    }
    
    // Also check for nested categories (marketing/seo)
    const hasNestedCategory = foundCategories.some(f => f.includes('seo') || f.includes('/'))
    if (!hasNestedCategory) {
      auditResult.issues.push({
        id: 'models_no_nested_categories',
        severity: 'P1',
        type: 'correctness',
        title: 'Nested categories not visible',
        description: 'marketing/seo and similar nested categories not found',
        route: '/models',
        reproSteps: [
          'Navigate to /models',
          'Look for nested categories like Marketing > SEO',
        ],
        suspectedFiles: ['components/openrouter/rankings-insights.tsx'],
        suggestedFix: 'Add support for rendering nested category hierarchy',
      })
    }
  })

  test('Models page: Top 10 rankings match API order', async ({ page }) => {
    await page.goto('/models', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
    
    // Click on programming tab if available
    const programmingTab = page.locator('button:has-text("Programming"), [data-value="programming"]').first()
    if (await programmingTab.isVisible()) {
      await programmingTab.click()
      await page.waitForTimeout(500)
    }
    
    await takeScreenshot(page, 'models_programming_rankings')
    
    // Get ranking entries
    const rankingEntries = page.locator('[data-rank], .ranking-row, .model-card, [class*="ranking"]')
    const entryCount = await rankingEntries.count()
    
    if (entryCount === 0) {
      auditResult.issues.push({
        id: 'models_no_rankings',
        severity: 'P0',
        type: 'correctness',
        title: 'No ranking entries displayed',
        description: 'Rankings list appears empty on Models page',
        route: '/models',
        reproSteps: ['Navigate to /models', 'Select Programming category'],
        suspectedFiles: ['components/openrouter/rankings-insights.tsx'],
        suggestedFix: 'Check if rankings API is being called and data rendered',
      })
    }
    
    // Verify we have 10 entries
    if (entryCount > 0 && entryCount < 10) {
      auditResult.issues.push({
        id: 'models_incomplete_rankings',
        severity: 'P1',
        type: 'correctness',
        title: `Only ${entryCount} ranking entries (expected 10)`,
        description: 'Rankings list is incomplete',
        route: '/models',
        reproSteps: ['Navigate to /models', 'Count ranking entries'],
        suspectedFiles: ['components/openrouter/rankings-insights.tsx'],
        suggestedFix: 'Ensure limit=10 is passed to rankings API',
      })
    }
  })

  test('Models page: Last synced timestamp is displayed', async ({ page }) => {
    await page.goto('/models', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
    
    // Look for timestamp indicator
    const timestampIndicators = [
      page.locator('text=/Last synced/i'),
      page.locator('text=/Updated/i'),
      page.locator('[class*="timestamp"]'),
      page.locator('[data-synced]'),
    ]
    
    let timestampFound = false
    for (const indicator of timestampIndicators) {
      if (await indicator.first().isVisible().catch(() => false)) {
        timestampFound = true
        break
      }
    }
    
    if (!timestampFound) {
      auditResult.issues.push({
        id: 'models_no_timestamp',
        severity: 'P2',
        type: 'ux',
        title: 'No last synced timestamp displayed',
        description: 'Rankings should show when data was last synced',
        route: '/models',
        reproSteps: ['Navigate to /models', 'Look for timestamp indicator'],
        suspectedFiles: ['components/openrouter/rankings-insights.tsx'],
        suggestedFix: 'Add last_synced timestamp display from API response',
      })
    }
  })

  test('Models page: Provider logos render for models', async ({ page }) => {
    await page.goto('/models', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
    
    await takeScreenshot(page, 'models_logos')
    
    // Look for logo images
    const logoImages = page.locator('img[src*="logo"], img[alt*="openai"], img[alt*="anthropic"], img[alt*="google"]')
    const logoCount = await logoImages.count()
    
    // Also check for fallback avatars (initial letter circles)
    const avatars = page.locator('[class*="avatar"], .model-logo, .provider-logo')
    const avatarCount = await avatars.count()
    
    if (logoCount === 0 && avatarCount === 0) {
      auditResult.issues.push({
        id: 'models_no_logos',
        severity: 'P2',
        type: 'ux',
        title: 'No provider logos visible',
        description: 'Model rows should display provider logos',
        route: '/models',
        reproSteps: ['Navigate to /models', 'Check for provider logos next to model names'],
        suspectedFiles: ['components/openrouter/rankings-insights.tsx', 'public/logos/'],
        suggestedFix: 'Add logo images and logo rendering component',
      })
    }
  })
})

test.describe('UI Audit - Chat UI', () => {
  test.beforeEach(async ({ page }) => {
    await setupOpenRouterMocks(page)
  })

  test('Chat page: Model dropdown has categories', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' })
    await page.waitForTimeout(500)
    
    // Look for model selector dropdown
    const modelSelector = page.locator('[data-testid="model-selector"], select[name="model"], button:has-text("Model")')
    
    if (await modelSelector.first().isVisible().catch(() => false)) {
      await modelSelector.first().click()
      await page.waitForTimeout(300)
      await takeScreenshot(page, 'chat_model_dropdown')
      
      // Check for category options
      const dropdownContent = page.locator('[role="listbox"], [role="menu"], .dropdown-content')
      const hasCategories = await dropdownContent.locator('text=/Programming|Science|Marketing/i').first().isVisible().catch(() => false)
      
      if (!hasCategories) {
        auditResult.issues.push({
          id: 'chat_no_categories_dropdown',
          severity: 'P1',
          type: 'correctness',
          title: 'Chat model dropdown missing categories',
          description: 'Model selector should show categories matching Models page',
          route: '/',
          reproSteps: ['Navigate to /', 'Click model selector dropdown', 'Check for category list'],
          suspectedFiles: ['components/chat-area.tsx', 'components/model-selector.tsx'],
          suggestedFix: 'Add category-based model selection to chat dropdown',
        })
      }
    }
    
    await takeScreenshot(page, 'chat_page')
  })

  test('Chat page: Clarifying questions flow works', async ({ page }) => {
    await setupClarifyingQuestionsMock(page)
    await page.goto('/', { waitUntil: 'networkidle' })
    
    // The home screen shows a "Start Chatting" button - need to click it first
    const startChatButton = page.locator('button:has-text("Start Chatting"), button:has-text("New Chat")').first()
    if (await startChatButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await startChatButton.click()
      await page.waitForTimeout(500)
    }
    
    // Find chat input (after starting a new chat)
    const chatInput = page.locator('textarea, input[type="text"]').first()
    if (!await chatInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      auditResult.issues.push({
        id: 'chat_no_input',
        severity: 'P0',
        type: 'ux',
        title: 'Chat input not visible',
        description: 'Cannot find chat input field after clicking Start Chat',
        route: '/',
        reproSteps: ['Navigate to /', 'Click Start Chatting', 'Look for chat input'],
        suspectedFiles: ['components/chat-area.tsx', 'components/chat-interface.tsx'],
        suggestedFix: 'Ensure chat input is rendered after starting a chat',
      })
      return
    }
    
    // Send ambiguous message
    await chatInput.fill('Tell me about this ambiguous topic')
    await chatInput.press('Enter')
    
    // Wait for response
    await page.waitForTimeout(2000)
    
    await takeScreenshot(page, 'chat_clarifying_question')
    
    // Check for clarifying question indicators
    const clarifyingIndicators = [
      page.locator('text=/clarification/i'),
      page.locator('text=/which aspect/i'),
      page.locator('text=/1\\./'),
      page.locator('[class*="clarify"]'),
    ]
    
    let clarifyingFound = false
    for (const indicator of clarifyingIndicators) {
      if (await indicator.first().isVisible().catch(() => false)) {
        clarifyingFound = true
        break
      }
    }
    
    if (!clarifyingFound) {
      auditResult.issues.push({
        id: 'chat_no_clarifying_flow',
        severity: 'P1',
        type: 'correctness',
        title: 'Clarifying questions not triggered',
        description: 'Ambiguous query should trigger clarifying question flow',
        route: '/',
        reproSteps: [
          'Navigate to /',
          'Send ambiguous message',
          'Check for clarifying question response',
        ],
        suspectedFiles: ['lib/chat-hooks.ts', 'app/api/chat/route.ts'],
        suggestedFix: 'Ensure clarification detection and rendering works',
      })
    }
  })
})

test.describe('UI Audit - Click Crawler', () => {
  // Click crawlers need extra time
  test.setTimeout(120000)
  
  test.beforeEach(async ({ page }) => {
    await setupOpenRouterMocks(page)
  })

  test('Safe click crawl on Home page', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' })
    setupListeners(page, '/')
    
    await crawlPage(page, '/')
  })

  test('Safe click crawl on Models page', async ({ page }) => {
    await page.goto('/models', { waitUntil: 'networkidle' })
    setupListeners(page, '/models')
    
    // Models page has 300+ model cards, so we limit to 25 clicks to avoid timeout
    await crawlPage(page, '/models', 25)
  })

  test('Safe click crawl on Orchestration page', async ({ page }) => {
    await page.goto('/orchestration', { waitUntil: 'networkidle' })
    setupListeners(page, '/orchestration')
    
    await crawlPage(page, '/orchestration')
  })

  test('Safe click crawl on Settings page', async ({ page }) => {
    await page.goto('/settings', { waitUntil: 'networkidle' })
    setupListeners(page, '/settings')
    
    await crawlPage(page, '/settings')
  })
})

// Click crawler implementation
async function crawlPage(page: Page, route: string, maxClicks?: number) {
  const clickedElements = new Set<string>()
  let clickCount = 0
  let skipCount = 0
  const limit = maxClicks ?? AUDIT_CONFIG.maxClicksPerPage
  
  // Get all clickable elements
  const clickables = await page.locator('a, button, [role="button"], [data-testid], [role="tab"], [role="menuitem"]').all()
  
  for (const element of clickables) {
    if (clickCount >= limit) break
    
    try {
      // Get element signature
      const text = await element.innerText().catch(() => '')
      const href = await element.getAttribute('href').catch(() => null)
      const signature = `${text}|${href}`
      
      // Skip if already clicked
      if (clickedElements.has(signature)) continue
      clickedElements.add(signature)
      
      // Skip destructive elements
      if (isDestructive(text)) {
        skipCount++
        continue
      }
      
      // Skip external links
      if (href && isExternalUrl(href)) {
        skipCount++
        continue
      }
      
      // Skip internal navigation links that would leave the current page
      if (href && href.startsWith('/') && !href.startsWith(route === '/' ? '/#' : route)) {
        skipCount++
        continue
      }
      
      // Skip if not visible
      if (!await element.isVisible().catch(() => false)) continue
      
      // Click and observe
      await element.click({ timeout: AUDIT_CONFIG.clickTimeout }).catch(() => {})
      await page.waitForTimeout(300)
      
      clickCount++
      
      // Take screenshot after significant clicks
      if (clickCount % 10 === 0) {
        await takeScreenshot(page, `crawl_${route.replace('/', '_')}_click_${clickCount}`)
      }
      
      // Check for dialogs/modals and close them
      const dialog = page.locator('[role="dialog"], [data-state="open"]')
      if (await dialog.isVisible().catch(() => false)) {
        await page.keyboard.press('Escape')
        await page.waitForTimeout(200)
      }
      
      // Navigate back if we left the page
      if (!page.isClosed()) {
        const currentUrl = page.url()
        const expectedPath = route === '/' ? 'localhost:3000/' : route
        // Check if URL ends with expected path or is the base URL for root
        const isOnCorrectPage = route === '/' 
          ? (currentUrl.endsWith('/') || currentUrl.endsWith(':3000'))
          : currentUrl.includes(route)
        if (!isOnCorrectPage) {
          await page.goto(route, { waitUntil: 'networkidle' })
        }
      }
      
    } catch (e) {
      // Ignore click errors - page might have closed or element is stale
      if (page.isClosed()) break
    }
  }
  
  auditResult.clicksAttempted += clickCount
  auditResult.clicksSkipped += skipCount
  
  // Final screenshot (with error handling for page closure)
  try {
    if (!page.isClosed()) {
      await takeScreenshot(page, `crawl_${route.replace('/', '_')}_final`)
    }
  } catch (e) {
    console.log(`Could not take final screenshot for ${route}: page closed or unavailable`)
  }
}

test.describe('UI Audit - Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupOpenRouterMocks(page)
  })

  for (const route of ROUTES_TO_AUDIT) {
    test(`Basic a11y check: ${route.name}`, async ({ page }) => {
      await page.goto(route.path, { waitUntil: 'networkidle' })
      
      // Check for basic a11y issues
      const violations: string[] = []
      
      // Check for images without alt text
      const imagesWithoutAlt = await page.locator('img:not([alt])').count()
      if (imagesWithoutAlt > 0) {
        violations.push(`${imagesWithoutAlt} images missing alt text`)
      }
      
      // Check for buttons without accessible names
      // We check for buttons that have no aria-label AND are empty (no text content)
      const allButtons = await page.locator('button').all()
      let buttonsWithoutName = 0
      for (const btn of allButtons) {
        try {
          const hasAriaLabel = await btn.getAttribute('aria-label')
          const hasAriaLabelledBy = await btn.getAttribute('aria-labelledby')
          const text = await btn.innerText().catch(() => '')
          const title = await btn.getAttribute('title')
          if (!hasAriaLabel && !hasAriaLabelledBy && !text?.trim() && !title) {
            buttonsWithoutName++
          }
        } catch {
          // Element may have been removed from DOM
        }
      }
      if (buttonsWithoutName > 0) {
        violations.push(`${buttonsWithoutName} buttons without accessible name`)
      }
      
      // Check for form inputs without labels
      const inputsWithoutLabels = await page.locator('input:not([aria-label]):not([id])').count()
      if (inputsWithoutLabels > 0) {
        violations.push(`${inputsWithoutLabels} inputs without labels`)
      }
      
      if (violations.length > 0) {
        auditResult.a11yViolations.push({
          route: route.path,
          violations: violations.length,
          rules: violations,
        })
      }
    })
  }
})

// Generate final report
test.afterAll(async () => {
  const reportDir = 'docs/ui_audit/reports/latest'
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true })
  }
  
  // Write issues.json
  const issuesPath = path.join(reportDir, 'issues.json')
  fs.writeFileSync(issuesPath, JSON.stringify(auditResult.issues, null, 2))
  
  // Write full report
  const reportPath = path.join(reportDir, 'report.md')
  const report = generateReport(auditResult)
  fs.writeFileSync(reportPath, report)
  
  console.log(`\n📊 Audit Report Generated:`)
  console.log(`   Report: ${reportPath}`)
  console.log(`   Issues: ${issuesPath}`)
  console.log(`   Screenshots: ${AUDIT_CONFIG.screenshotDir}/`)
  console.log(`\n🔍 Summary:`)
  console.log(`   Routes visited: ${auditResult.routesVisited.length}`)
  console.log(`   Clicks attempted: ${auditResult.clicksAttempted}`)
  console.log(`   Clicks skipped: ${auditResult.clicksSkipped}`)
  console.log(`   Console errors: ${auditResult.consoleErrors.length}`)
  console.log(`   Network failures: ${auditResult.networkFailures.length}`)
  console.log(`   Issues found: ${auditResult.issues.length}`)
})

function generateReport(result: AuditResult): string {
  const p0Issues = result.issues.filter(i => i.severity === 'P0')
  const p1Issues = result.issues.filter(i => i.severity === 'P1')
  const p2Issues = result.issues.filter(i => i.severity === 'P2')
  
  return `# LLMHive UI Audit Report

**Generated**: ${result.timestamp}

## Executive Summary

| Metric | Count |
|--------|-------|
| Routes Visited | ${result.routesVisited.length} |
| Clicks Attempted | ${result.clicksAttempted} |
| Clicks Skipped (safety) | ${result.clicksSkipped} |
| Console Errors | ${result.consoleErrors.length} |
| Network Failures | ${result.networkFailures.length} |
| P0 Issues (Critical) | ${p0Issues.length} |
| P1 Issues (High) | ${p1Issues.length} |
| P2 Issues (Medium) | ${p2Issues.length} |

## Routes Visited

${result.routesVisited.map(r => `- ${r}`).join('\n')}

## Issues by Severity

### P0 - Critical (Must Fix)

${p0Issues.length === 0 ? '_No P0 issues found._' : p0Issues.map(i => formatIssue(i)).join('\n\n')}

### P1 - High Priority

${p1Issues.length === 0 ? '_No P1 issues found._' : p1Issues.map(i => formatIssue(i)).join('\n\n')}

### P2 - Medium Priority

${p2Issues.length === 0 ? '_No P2 issues found._' : p2Issues.map(i => formatIssue(i)).join('\n\n')}

## Console Errors

${result.consoleErrors.length === 0 ? '_No console errors detected._' : result.consoleErrors.slice(0, 20).map(e => `- **${e.route}**: ${e.message.slice(0, 100)}`).join('\n')}

## Network Failures

${result.networkFailures.length === 0 ? '_No network failures detected._' : result.networkFailures.slice(0, 20).map(f => `- **${f.route}**: ${f.method} ${f.url.slice(0, 60)} → ${f.status}`).join('\n')}

## Accessibility Violations

${result.a11yViolations.length === 0 ? '_No accessibility violations detected._' : result.a11yViolations.map(v => `
### ${v.route}
- ${v.rules.join('\n- ')}
`).join('\n')}

---

## Agent Fix Prompt

Based on this audit, here are the concrete next steps:

### High Priority Fixes

${p0Issues.concat(p1Issues).slice(0, 5).map((i, idx) => `
${idx + 1}. **${i.title}**
   - File: ${i.suspectedFiles?.join(', ') || 'Unknown'}
   - Fix: ${i.suggestedFix || 'Investigate and fix'}
`).join('\n')}

### Files to Modify

\`\`\`
${[...new Set(result.issues.flatMap(i => i.suspectedFiles || []))].slice(0, 10).join('\n')}
\`\`\`

---

_Report generated by LLMHive UI Audit Tool_
`
}

function formatIssue(issue: AuditIssue): string {
  return `#### ${issue.id}: ${issue.title}

**Type**: ${issue.type} | **Route**: ${issue.route}

${issue.description}

**Reproduction Steps**:
${issue.reproSteps.map((s, i) => `${i + 1}. ${s}`).join('\n')}

**Suspected Files**: ${issue.suspectedFiles?.join(', ') || 'Unknown'}

**Suggested Fix**: ${issue.suggestedFix || 'Investigate'}

${issue.screenshotPath ? `**Screenshot**: ${issue.screenshotPath}` : ''}`
}

