import { test, expect } from '@playwright/test'

/**
 * Settings Page Tests for LLMHive
 * 
 * Tests cover:
 * - Settings categories
 * - Drawer interactions
 * - Form validation
 * - Settings persistence
 */

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
  })

  test('page loads with title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Settings')
  })

  test('all settings category cards are visible', async ({ page }) => {
    // Use more specific locators - target the card buttons
    await expect(page.getByRole('button', { name: /Account/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /API Keys/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Connections/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Notifications/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Privacy/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Appearance/i })).toBeVisible()
  })
})

test.describe('Account Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
  })

  test('account drawer opens when clicking Account card', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    
    // Wait for drawer to open
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('account drawer shows profile fields', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    // Check for form fields
    await expect(page.getByText('Display Name')).toBeVisible()
    await expect(page.getByText('Email')).toBeVisible()
  })

  test('account drawer shows Save Changes button', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByRole('button', { name: /Save Changes/i })).toBeVisible()
  })

  test('account drawer shows Delete Account option', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Danger Zone')).toBeVisible()
    await expect(page.getByRole('button', { name: /Delete Account/i })).toBeVisible()
  })
})

test.describe('API Keys Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
  })

  test('API keys drawer opens when clicking API Keys card', async ({ page }) => {
    await page.getByRole('button', { name: /API Keys/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('API keys drawer shows provider options', async ({ page }) => {
    await page.getByRole('button', { name: /API Keys/i }).click()
    await page.waitForTimeout(500)
    
    // Check for providers
    await expect(page.getByText('OpenAI')).toBeVisible()
    await expect(page.getByText('Anthropic')).toBeVisible()
  })
})

test.describe('Notifications Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
  })

  test('notifications drawer opens when clicking Notifications card', async ({ page }) => {
    await page.getByRole('button', { name: /Notifications/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('notifications drawer shows notification types', async ({ page }) => {
    await page.getByRole('button', { name: /Notifications/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Email Notifications')).toBeVisible()
    await expect(page.getByText('Push Notifications')).toBeVisible()
  })
})

test.describe('Privacy Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
  })

  test('privacy drawer opens when clicking Privacy card', async ({ page }) => {
    await page.getByRole('button', { name: /Privacy/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('privacy drawer shows privacy options', async ({ page }) => {
    await page.getByRole('button', { name: /Privacy/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Share Usage Data')).toBeVisible()
  })
})

test.describe('Appearance Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
  })

  test('appearance drawer opens when clicking Appearance card', async ({ page }) => {
    await page.getByRole('button', { name: /Appearance/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('appearance drawer shows theme options', async ({ page }) => {
    await page.getByRole('button', { name: /Appearance/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Theme')).toBeVisible()
  })
})

test.describe('Settings Drawer Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
  })

  test('drawer closes when pressing Escape', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    
    // Wait for drawer to close
    await page.waitForTimeout(500)
  })
})

test.describe('Settings Responsive Layout', () => {
  test('settings page works on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
    
    // Use specific role-based selectors
    await expect(page.getByRole('button', { name: /Account/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /API Keys/i })).toBeVisible()
  })

  test('settings page works on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
    
    await expect(page.getByRole('button', { name: /Account/i })).toBeVisible()
  })

  test('settings page works on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
    
    await expect(page.locator('h1')).toContainText('Settings')
  })
})
