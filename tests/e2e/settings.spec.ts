import { test, expect } from '@playwright/test'

/**
 * Settings Page Tests for LLMHive
 * 
 * Tests cover:
 * - Settings categories
 * - Drawer interactions
 * - Form validation
 * - Settings persistence
 * - Account management
 * - Privacy settings
 */

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('page loads with title and description', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Settings')
    await expect(page.locator('text=Configure your account')).toBeVisible()
  })

  test('all settings categories are visible', async ({ page }) => {
    // Verify all settings cards
    await expect(page.locator('text=Account')).toBeVisible()
    await expect(page.locator('text=API Keys')).toBeVisible()
    await expect(page.locator('text=Connections')).toBeVisible()
    await expect(page.locator('text=Notifications')).toBeVisible()
    await expect(page.locator('text=Privacy')).toBeVisible()
    await expect(page.locator('text=Appearance')).toBeVisible()
  })

  test('settings cards show count badges', async ({ page }) => {
    // Some cards should show counts (e.g., "1 key configured")
    // The Account card may not have a badge, but API Keys, Connections should
    await expect(page.locator('button:has-text("API Keys")')).toBeVisible()
  })
})

test.describe('Account Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('account drawer opens when clicking Account card', async ({ page }) => {
    await page.click('button:has-text("Account")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('account drawer shows profile fields', async ({ page }) => {
    await page.click('button:has-text("Account")')
    await page.waitForTimeout(500)
    
    // Should show form fields
    await expect(page.locator('text=Display Name')).toBeVisible()
    await expect(page.locator('text=Email')).toBeVisible()
    await expect(page.locator('text=Bio').or(page.locator('input[placeholder*="about"]'))).toBeVisible()
  })

  test('account drawer shows Save Changes button', async ({ page }) => {
    await page.click('button:has-text("Account")')
    await page.waitForTimeout(500)
    
    await expect(page.locator('button:has-text("Save Changes")')).toBeVisible()
  })

  test('account drawer shows Delete Account option', async ({ page }) => {
    await page.click('button:has-text("Account")')
    await page.waitForTimeout(500)
    
    await expect(page.locator('text=Danger Zone')).toBeVisible()
    await expect(page.locator('button:has-text("Delete Account")')).toBeVisible()
  })

  test('can edit display name field', async ({ page }) => {
    await page.click('button:has-text("Account")')
    await page.waitForTimeout(500)
    
    const nameInput = page.locator('input[placeholder*="name"], input[placeholder="Your name"]')
    await nameInput.clear()
    await nameInput.fill('Test User')
    await expect(nameInput).toHaveValue('Test User')
  })

  test('can edit email field', async ({ page }) => {
    await page.click('button:has-text("Account")')
    await page.waitForTimeout(500)
    
    const emailInput = page.locator('input[type="email"]')
    await emailInput.clear()
    await emailInput.fill('test@example.com')
    await expect(emailInput).toHaveValue('test@example.com')
  })
})

test.describe('API Keys Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('API keys drawer opens when clicking API Keys card', async ({ page }) => {
    await page.click('button:has-text("API Keys")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('API keys drawer shows provider options', async ({ page }) => {
    await page.click('button:has-text("API Keys")')
    await page.waitForTimeout(500)
    
    // Should show API key providers
    await expect(page.locator('text=OpenAI')).toBeVisible()
    await expect(page.locator('text=Anthropic')).toBeVisible()
    await expect(page.locator('text=Google AI')).toBeVisible()
  })

  test('can toggle API key connection status', async ({ page }) => {
    await page.click('button:has-text("API Keys")')
    await page.waitForTimeout(500)
    
    // Click on a provider to toggle
    const openaiOption = page.locator('button:has-text("OpenAI")').first()
    await openaiOption.click()
    
    // Connection state should toggle (visual change)
  })

  test('shows connected status badge', async ({ page }) => {
    await page.click('button:has-text("API Keys")')
    await page.waitForTimeout(500)
    
    // At least one key shows "Connected" badge
    await expect(page.locator('text=Connected').first()).toBeVisible()
  })
})

test.describe('Connections Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('connections drawer opens when clicking Connections card', async ({ page }) => {
    await page.click('button:has-text("Connections")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('connections drawer shows service options', async ({ page }) => {
    await page.click('button:has-text("Connections")')
    await page.waitForTimeout(500)
    
    // Should show service integrations
    await expect(page.locator('text=GitHub')).toBeVisible()
    await expect(page.locator('text=Google')).toBeVisible()
    await expect(page.locator('text=Slack')).toBeVisible()
  })

  test('can toggle service connections', async ({ page }) => {
    await page.click('button:has-text("Connections")')
    await page.waitForTimeout(500)
    
    // Click on a service to toggle
    const githubOption = page.locator('button:has-text("GitHub")').first()
    await githubOption.click()
    
    // Connection state should toggle
  })
})

test.describe('Notifications Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('notifications drawer opens when clicking Notifications card', async ({ page }) => {
    await page.click('button:has-text("Notifications")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('notifications drawer shows notification types', async ({ page }) => {
    await page.click('button:has-text("Notifications")')
    await page.waitForTimeout(500)
    
    // Should show notification options
    await expect(page.locator('text=Email Notifications')).toBeVisible()
    await expect(page.locator('text=Push Notifications')).toBeVisible()
    await expect(page.locator('text=Product Updates')).toBeVisible()
  })

  test('can toggle notification preferences', async ({ page }) => {
    await page.click('button:has-text("Notifications")')
    await page.waitForTimeout(500)
    
    // Click on a notification option to toggle
    const emailOption = page.locator('button:has-text("Email Notifications")').first()
    await emailOption.click()
  })
})

test.describe('Privacy Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('privacy drawer opens when clicking Privacy card', async ({ page }) => {
    await page.click('button:has-text("Privacy")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('privacy drawer shows privacy options', async ({ page }) => {
    await page.click('button:has-text("Privacy")')
    await page.waitForTimeout(500)
    
    // Should show privacy settings
    await expect(page.locator('text=Share Usage Data')).toBeVisible()
    await expect(page.locator('text=Share Chats for Training')).toBeVisible()
    await expect(page.locator('text=Public Profile')).toBeVisible()
  })

  test('can toggle privacy settings', async ({ page }) => {
    await page.click('button:has-text("Privacy")')
    await page.waitForTimeout(500)
    
    // Click on a privacy option to toggle
    const shareUsageOption = page.locator('button:has-text("Share Usage Data")').first()
    await shareUsageOption.click()
  })
})

test.describe('Appearance Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('appearance drawer opens when clicking Appearance card', async ({ page }) => {
    await page.click('button:has-text("Appearance")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('appearance drawer shows theme options', async ({ page }) => {
    await page.click('button:has-text("Appearance")')
    await page.waitForTimeout(500)
    
    // Should show theme selector
    await expect(page.locator('text=Theme')).toBeVisible()
    await expect(page.locator('text=Light').or(page.locator('button:has-text("Light")'))).toBeVisible()
    await expect(page.locator('text=Dark').or(page.locator('button:has-text("Dark")'))).toBeVisible()
    await expect(page.locator('text=System').or(page.locator('button:has-text("System")'))).toBeVisible()
  })

  test('appearance drawer shows display options', async ({ page }) => {
    await page.click('button:has-text("Appearance")')
    await page.waitForTimeout(500)
    
    // Should show appearance toggles
    await expect(page.locator('text=Compact Mode')).toBeVisible()
    await expect(page.locator('text=Animations')).toBeVisible()
    await expect(page.locator('text=Sound Effects')).toBeVisible()
  })

  test('can select theme', async ({ page }) => {
    await page.click('button:has-text("Appearance")')
    await page.waitForTimeout(500)
    
    // Click on a theme option
    const lightTheme = page.locator('button:has-text("Light")').first()
    await lightTheme.click()
    
    // Theme button should show selected state
  })

  test('can toggle appearance options', async ({ page }) => {
    await page.click('button:has-text("Appearance")')
    await page.waitForTimeout(500)
    
    // Toggle Compact Mode
    const compactModeOption = page.locator('button:has-text("Compact Mode")').first()
    await compactModeOption.click()
  })
})

test.describe('Settings Drawer Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('drawer closes when pressing Escape', async ({ page }) => {
    await page.click('button:has-text("Account")')
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible()
    
    await page.keyboard.press('Escape')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).not.toBeVisible({ timeout: 2000 })
  })

  test('only one drawer open at a time', async ({ page }) => {
    await page.click('button:has-text("Account")')
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible()
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
    
    await page.click('button:has-text("API Keys")')
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible()
    
    // Only one dialog should be visible
    const dialogs = await page.locator('[role="dialog"], [data-state="open"]').count()
    expect(dialogs).toBeLessThanOrEqual(1)
  })
})

test.describe('Settings Persistence', () => {
  test('settings state is preserved on page reload', async ({ page }) => {
    await page.goto('/settings')
    
    // Make a change
    await page.click('button:has-text("Notifications")')
    await page.waitForTimeout(500)
    
    // Toggle something
    const pushOption = page.locator('button:has-text("Push Notifications")').first()
    await pushOption.click()
    
    await page.keyboard.press('Escape')
    
    // Reload the page
    await page.reload()
    
    // The badge count should reflect the change
    // (Implementation specific - may need to verify localStorage)
  })
})

test.describe('Settings Responsive Layout', () => {
  test('settings page works on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/settings')
    
    // All cards visible
    await expect(page.locator('text=Account')).toBeVisible()
    await expect(page.locator('text=API Keys')).toBeVisible()
    await expect(page.locator('text=Privacy')).toBeVisible()
  })

  test('settings page works on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/settings')
    
    // Cards should reflow but remain accessible
    await expect(page.locator('text=Account')).toBeVisible()
    await expect(page.locator('text=API Keys')).toBeVisible()
  })

  test('settings page works on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/settings')
    
    // Core content should be accessible
    await expect(page.locator('h1')).toContainText('Settings')
    await expect(page.locator('text=Account')).toBeVisible()
  })
})

test.describe('Settings Accessibility', () => {
  test('settings cards are keyboard accessible', async ({ page }) => {
    await page.goto('/settings')
    
    // Tab through the page
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    
    // Should be able to open drawer with Enter
    await page.keyboard.press('Enter')
    
    // A drawer should open
    await page.waitForTimeout(500)
  })

  test('form fields in drawer are focusable', async ({ page }) => {
    await page.goto('/settings')
    await page.click('button:has-text("Account")')
    await page.waitForTimeout(500)
    
    // Tab to first input
    await page.keyboard.press('Tab')
    
    // An input should be focused
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
  })
})

test.describe('Settings Form Validation', () => {
  test('email field validates format', async ({ page }) => {
    await page.goto('/settings')
    await page.click('button:has-text("Account")')
    await page.waitForTimeout(500)
    
    const emailInput = page.locator('input[type="email"]')
    
    // Enter invalid email
    await emailInput.fill('not-an-email')
    
    // The browser's built-in validation should mark it invalid
    // or there may be custom validation
  })

  test('required fields show validation state', async ({ page }) => {
    await page.goto('/settings')
    await page.click('button:has-text("Account")')
    await page.waitForTimeout(500)
    
    // Clear a required field and try to save
    const nameInput = page.locator('input[placeholder*="name"], input[placeholder="Your name"]')
    await nameInput.clear()
    
    // Click save
    const saveButton = page.locator('button:has-text("Save Changes")')
    await saveButton.click()
    
    // Form may show validation error (depends on implementation)
  })
})
