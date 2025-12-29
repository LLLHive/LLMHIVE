import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for LLMHive E2E testing.
 * 
 * @see https://playwright.dev/docs/test-configuration
 * 
 * Run tests with:
 * - npm run test:e2e           - Run all E2E tests (Chromium)
 * - npm run test:e2e:ui        - Run with Playwright UI
 * - npm run test:e2e:headed    - Run tests with visible browser
 * - npm run test:e2e:all       - Run on all browsers
 */

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*.spec.ts',
  
  // Run tests in parallel
  fullyParallel: true,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Limit workers on CI for stability
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter configuration
  reporter: process.env.CI 
    ? [['list'], ['html', { outputFolder: 'playwright-report' }]]
    : [['list']],
  
  // Output directory for test artifacts
  outputDir: 'test-results/',
  
  // Global timeout for each test - increased for dev server
  timeout: 60000,
  
  // Expect timeout
  expect: {
    timeout: 15000,
  },

  // Shared settings for all projects
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    viewport: { width: 1280, height: 720 },
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  // Configure projects - Chromium only by default for speed
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Run local dev server before starting the tests
  // In CI, we start the server manually (npm start after build), so reuse it
  webServer: {
    command: process.env.CI ? 'npm start' : 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true, // Always reuse if server is already running
    timeout: 120 * 1000,
  },
})
