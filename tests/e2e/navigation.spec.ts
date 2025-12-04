import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('home page loads with welcome message', async ({ page }) => {
    await page.goto('/')
    
    // Verify home page loads with welcome text
    await expect(page.locator('text=Welcome to LLMHive')).toBeVisible({ timeout: 10000 })
  })

  test('sidebar navigation links work correctly', async ({ page }) => {
    await page.goto('/')
    
    // Navigate to Discover
    await page.click('a[href="/discover"]')
    await expect(page).toHaveURL('/discover')
    await expect(page.locator('h1')).toContainText('Discover')

    // Navigate to Orchestration
    await page.click('a[href="/orchestration"]')
    await expect(page).toHaveURL('/orchestration')
    await expect(page.locator('h1')).toContainText('Orchestration')

    // Navigate to Settings
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL('/settings')
    await expect(page.locator('h1')).toContainText('Settings')
  })

  test('logo click returns to home from any page', async ({ page }) => {
    // Start on settings page
    await page.goto('/settings')
    await expect(page.locator('h1')).toContainText('Settings')
    
    // Click logo to return home
    await page.click('img[alt="LLMHive"]')
    await expect(page).toHaveURL('/')
  })

  test('new chat button creates new conversation', async ({ page }) => {
    await page.goto('/')
    
    // Click "New Chat" button
    await page.click('button:has-text("New Chat")')
    
    // Should see the chat input area
    await expect(page.locator('textarea[placeholder*="Ask"]')).toBeVisible()
  })
})

test.describe('Mobile Navigation', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test('hamburger menu opens sidebar on mobile', async ({ page }) => {
    await page.goto('/')
    
    // Click hamburger menu
    await page.click('button:has(svg.lucide-menu)')
    
    // Sidebar should be visible
    await expect(page.locator('text=Discover')).toBeVisible()
    await expect(page.locator('text=Settings')).toBeVisible()
  })
})

test.describe('Page Loading States', () => {
  test('discover page loads without errors', async ({ page }) => {
    await page.goto('/discover')
    
    // Should show discover content
    await expect(page.locator('h1')).toContainText('Discover')
    await expect(page.locator('text=Web Search')).toBeVisible()
    await expect(page.locator('text=Knowledge Base')).toBeVisible()
  })

  test('orchestration page loads without errors', async ({ page }) => {
    await page.goto('/orchestration')
    
    // Should show orchestration content
    await expect(page.locator('h1')).toContainText('Orchestration')
    await expect(page.locator('text=Models')).toBeVisible()
    await expect(page.locator('text=Reasoning')).toBeVisible()
  })

  test('settings page loads without errors', async ({ page }) => {
    await page.goto('/settings')
    
    // Should show settings content
    await expect(page.locator('h1')).toContainText('Settings')
    await expect(page.locator('text=Account')).toBeVisible()
    await expect(page.locator('text=API Keys')).toBeVisible()
  })
})

test.describe('Error Handling', () => {
  test('404 page shows for invalid routes', async ({ page }) => {
    const response = await page.goto('/this-page-does-not-exist')
    
    // Next.js should return 404
    expect(response?.status()).toBe(404)
  })
})
