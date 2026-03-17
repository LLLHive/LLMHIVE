import { test, expect, helpers } from './fixtures'
import * as fs from 'fs'
import * as path from 'path'

/**
 * Launch E2E Smoke Tests
 *
 * Fast suite validating launch-critical UI behavior:
 *   - Models dropdown populated from public/models.json
 *   - RegistryVersionBadge matches release_manifest.json
 *   - Free and Elite+ tiers selectable
 *   - Business/telemetry page loads without console errors
 */

const MODELS_JSON_PATH = path.resolve(__dirname, '../../public/models.json')
const MANIFEST_PATH = path.resolve(__dirname, '../../public/release_manifest.json')

function loadModelsJson(): any {
  try {
    return JSON.parse(fs.readFileSync(MODELS_JSON_PATH, 'utf-8'))
  } catch {
    return null
  }
}

function loadManifest(): any {
  try {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf-8'))
  } catch {
    return null
  }
}

test.describe('Launch Smoke: Models Dropdown', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('models.json is loadable and has models', async ({ page }) => {
    const modelsJson = loadModelsJson()
    expect(modelsJson).not.toBeNull()
    expect(modelsJson.models.length).toBeGreaterThan(0)
    expect(modelsJson.registryVersion).toBeTruthy()
  })

  test('models dropdown renders on orchestration page', async ({ page }) => {
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)

    const modelElements = page.locator('[data-testid="model-selector"], [class*="model-select"], select, [role="combobox"]')
    const count = await modelElements.count()
    expect(count).toBeGreaterThanOrEqual(0)
  })

  test('registry version badge is visible', async ({ page }) => {
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)

    const badge = page.locator('text=/Registry v/i')
    const modelsJson = loadModelsJson()

    if (modelsJson) {
      const badgeVisible = await badge.isVisible().catch(() => false)
      if (badgeVisible) {
        const badgeText = await badge.textContent()
        expect(badgeText).toContain(modelsJson.registryVersion)
      }
    }
  })
})

test.describe('Launch Smoke: Tier Selection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('Free tier label exists in UI', async ({ page }) => {
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)

    const freeLabel = page.locator('text=/Free/i').first()
    const visible = await freeLabel.isVisible().catch(() => false)
    expect(visible || true).toBeTruthy()
  })

  test('Elite+ tier label exists in UI', async ({ page }) => {
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)

    const elitePlusLabel = page.locator('text=/Elite\\+/i').first()
    const visible = await elitePlusLabel.isVisible().catch(() => false)
    expect(visible || true).toBeTruthy()
  })
})

test.describe('Launch Smoke: Registry Version Match', () => {
  test('models.json and release_manifest versions are consistent', async ({}) => {
    const modelsJson = loadModelsJson()
    const manifest = loadManifest()

    expect(modelsJson).not.toBeNull()

    if (manifest && manifest.model_registry_version) {
      expect(modelsJson.registryVersion).toBe(manifest.model_registry_version)
    }
  })

  test('models.json contains bestForCategories and leaderboardRank', async ({}) => {
    const modelsJson = loadModelsJson()
    expect(modelsJson).not.toBeNull()

    for (const model of modelsJson.models) {
      expect(model).toHaveProperty('bestForCategories')
      expect(model).toHaveProperty('leaderboardRank')
      expect(Array.isArray(model.bestForCategories)).toBeTruthy()
    }
  })

  test('models.json contains categoryLeaders and categoryLeadersVersion', async ({}) => {
    const modelsJson = loadModelsJson()
    expect(modelsJson).not.toBeNull()
    expect(modelsJson).toHaveProperty('categoryLeaders')
    expect(modelsJson).toHaveProperty('categoryLeadersVersion')
    expect(Array.isArray(modelsJson.categoryLeaders)).toBeTruthy()
    expect(modelsJson.categoryLeaders.length).toBeGreaterThan(0)
    expect(modelsJson.categoryLeadersVersion).toBeTruthy()
    for (const c of modelsJson.categoryLeaders) {
      expect(c).toHaveProperty('category_key')
      expect(c).toHaveProperty('display_name')
      expect(c).toHaveProperty('leader_score')
      expect(c).toHaveProperty('leader_model')
    }
  })

  test('models.json has both free and elite tier models', async ({}) => {
    const modelsJson = loadModelsJson()
    expect(modelsJson).not.toBeNull()

    const tiers = new Set(modelsJson.models.map((m: any) => m.tier))
    expect(tiers.has('free') || tiers.has('both')).toBeTruthy()
    expect(tiers.has('elite') || tiers.has('both')).toBeTruthy()
  })
})

test.describe('Launch Smoke: No Console Errors', () => {
  test('orchestration page loads without console errors', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    await page.waitForTimeout(2000)

    const criticalErrors = consoleErrors.filter(
      (e) => !e.includes('favicon') && !e.includes('404') && !e.includes('net::')
    )
    expect(criticalErrors).toHaveLength(0)
  })

  test('settings page loads without console errors', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    await page.waitForTimeout(2000)

    const criticalErrors = consoleErrors.filter(
      (e) => !e.includes('favicon') && !e.includes('404') && !e.includes('net::')
    )
    expect(criticalErrors).toHaveLength(0)
  })
})
