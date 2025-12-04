import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for LLMHive E2E testing.
 * 
 * @see https://playwright.dev/docs/test-configuration
 * 
 * Run tests with:
 * - npm run test:e2e           - Run all E2E tests
 * - npm run test:e2e:ui        - Run with Playwright UI
 * - npm run test:e2e:headed    - Run tests with visible browser
 * - npm run test:e2e:debug     - Run in debug mode
 * - npm run test:e2e:chromium  - Run only Chromium tests
 */

export default defineConfig({
  // Test directory
  testDir: './tests/e2e',
  
  // Test file patterns
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
    ? [
        ['list'],
        ['html', { outputFolder: 'playwright-report' }],
        ['json', { outputFile: 'test-results/results.json' }],
        ['junit', { outputFile: 'test-results/junit.xml' }],
      ]
    : [['html', { open: 'never' }]],
  
  // Output directory for test artifacts
  outputDir: 'test-results/',
  
  // Global timeout for each test
  timeout: 30000,
  
  // Expect timeout
  expect: {
    timeout: 10000,
  },

  // Shared settings for all projects
  use: {
    // Base URL for all tests
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    
    // Collect trace when retrying the failed test
    trace: process.env.CI ? 'on-first-retry' : 'retain-on-failure',
    
    // Take screenshot on failure
    screenshot: 'only-on-failure',
    
    // Record video on failure
    video: process.env.CI ? 'on-first-retry' : 'off',
    
    // Browser context options
    viewport: { width: 1280, height: 720 },
    
    // Ignore HTTPS errors
    ignoreHTTPSErrors: true,
    
    // Action timeout
    actionTimeout: 10000,
    
    // Navigation timeout
    navigationTimeout: 30000,
  },

  // Configure projects for major browsers
  projects: [
    // Desktop browsers
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--disable-web-security'],
        },
      },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Mobile viewports
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
    
    // Tablet viewport
    {
      name: 'tablet',
      use: {
        viewport: { width: 768, height: 1024 },
        isMobile: false,
      },
    },
  ],

  // Run local dev server before starting the tests
  webServer: {
    command: process.env.CI 
      ? 'npm run build && npm run start'  // Production build on CI
      : 'npm run dev',                     // Dev server locally
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
})
