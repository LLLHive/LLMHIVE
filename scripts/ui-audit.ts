#!/usr/bin/env npx ts-node

/**
 * LLMHive UI Audit Script
 * 
 * Runs a comprehensive UI audit including:
 * - Route discovery and navigation testing
 * - OpenRouter rankings validation
 * - Click crawler with safety checks
 * - Console/network error detection
 * - Accessibility checks
 * 
 * Usage:
 *   npm run ui:audit           - Run full audit
 *   npm run ui:audit:quick     - Run quick smoke test
 */

import { execSync, spawn, ChildProcess } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'

const REPORT_DIR = 'docs/ui_audit/reports'
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)

interface AuditConfig {
  mode: 'full' | 'quick'
  headed: boolean
  updateSnapshots: boolean
}

function parseArgs(): AuditConfig {
  const args = process.argv.slice(2)
  return {
    mode: args.includes('--quick') ? 'quick' : 'full',
    headed: args.includes('--headed'),
    updateSnapshots: args.includes('--update-snapshots'),
  }
}

function log(message: string, type: 'info' | 'success' | 'error' | 'warn' = 'info') {
  const icons = { info: '📋', success: '✅', error: '❌', warn: '⚠️' }
  console.log(`${icons[type]} ${message}`)
}

function ensureDirectories() {
  const dirs = [
    REPORT_DIR,
    path.join(REPORT_DIR, TIMESTAMP),
    path.join(REPORT_DIR, TIMESTAMP, 'screenshots'),
    path.join(REPORT_DIR, 'latest'),
    path.join(REPORT_DIR, 'latest', 'screenshots'),
  ]
  
  for (const dir of dirs) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
  }
}

function checkDependencies() {
  log('Checking dependencies...')
  
  try {
    execSync('npx playwright --version', { stdio: 'pipe' })
  } catch {
    log('Playwright not found. Installing...', 'warn')
    execSync('npm run test:e2e:install', { stdio: 'inherit' })
  }
}

function startDevServer(): ChildProcess | null {
  log('Starting development server...')
  
  // Check if server is already running
  try {
    const response = execSync('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000', { 
      stdio: 'pipe',
      timeout: 5000,
    })
    if (response.toString().trim() === '200') {
      log('Development server already running on port 3000', 'success')
      return null
    }
  } catch {
    // Server not running, start it
  }
  
  const server = spawn('npm', ['run', 'dev'], {
    stdio: 'pipe',
    detached: true,
  })
  
  // Wait for server to be ready
  log('Waiting for server to start...')
  let attempts = 0
  const maxAttempts = 30
  
  while (attempts < maxAttempts) {
    try {
      execSync('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000', { 
        stdio: 'pipe',
        timeout: 2000,
      })
      log('Development server is ready', 'success')
      break
    } catch {
      attempts++
      execSync('sleep 2')
    }
  }
  
  if (attempts >= maxAttempts) {
    log('Failed to start development server', 'error')
    process.exit(1)
  }
  
  return server
}

function runAuditTests(config: AuditConfig) {
  log(`Running ${config.mode} UI audit...`)
  
  const testPattern = config.mode === 'quick' 
    ? 'tests/e2e/audit/ui-audit.spec.ts -g "Route loads"'
    : 'tests/e2e/audit/ui-audit.spec.ts'
  
  const playwrightArgs = [
    'playwright', 'test',
    testPattern,
    '--project=chromium',
    '--reporter=list,html',
    `--output=test-results/audit-${TIMESTAMP}`,
  ]
  
  if (config.headed) {
    playwrightArgs.push('--headed')
  }
  
  if (config.updateSnapshots) {
    playwrightArgs.push('--update-snapshots')
  }
  
  try {
    execSync(`npx ${playwrightArgs.join(' ')}`, { 
      stdio: 'inherit',
      env: {
        ...process.env,
        PLAYWRIGHT_BASE_URL: 'http://localhost:3000',
      },
    })
    log('UI audit tests completed', 'success')
  } catch (error) {
    log('Some audit tests failed (see report for details)', 'warn')
  }
}

function copyReportToTimestamped() {
  const latestDir = path.join(REPORT_DIR, 'latest')
  const timestampDir = path.join(REPORT_DIR, TIMESTAMP)
  
  // Copy report files
  const files = ['report.md', 'issues.json']
  for (const file of files) {
    const src = path.join(latestDir, file)
    const dst = path.join(timestampDir, file)
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dst)
    }
  }
  
  // Copy screenshots
  const screenshotsSrc = path.join(latestDir, 'screenshots')
  const screenshotsDst = path.join(timestampDir, 'screenshots')
  if (fs.existsSync(screenshotsSrc)) {
    const screenshots = fs.readdirSync(screenshotsSrc)
    for (const screenshot of screenshots) {
      fs.copyFileSync(
        path.join(screenshotsSrc, screenshot),
        path.join(screenshotsDst, screenshot)
      )
    }
  }
  
  log(`Report copied to ${timestampDir}`, 'success')
}

function printSummary() {
  const reportPath = path.join(REPORT_DIR, 'latest', 'report.md')
  const issuesPath = path.join(REPORT_DIR, 'latest', 'issues.json')
  
  console.log('\n' + '='.repeat(60))
  console.log('📊 UI AUDIT COMPLETE')
  console.log('='.repeat(60))
  
  if (fs.existsSync(issuesPath)) {
    const issues = JSON.parse(fs.readFileSync(issuesPath, 'utf-8'))
    const p0 = issues.filter((i: any) => i.severity === 'P0').length
    const p1 = issues.filter((i: any) => i.severity === 'P1').length
    const p2 = issues.filter((i: any) => i.severity === 'P2').length
    
    console.log('\n📈 Issue Summary:')
    console.log(`   P0 (Critical): ${p0}`)
    console.log(`   P1 (High):     ${p1}`)
    console.log(`   P2 (Medium):   ${p2}`)
    console.log(`   Total:         ${issues.length}`)
    
    if (issues.length > 0) {
      console.log('\n🔝 Top Issues:')
      issues.slice(0, 10).forEach((issue: any, i: number) => {
        console.log(`   ${i + 1}. [${issue.severity}] ${issue.title}`)
      })
    }
  }
  
  console.log('\n📁 Report Files:')
  console.log(`   Full Report:  ${reportPath}`)
  console.log(`   Issues JSON:  ${issuesPath}`)
  console.log(`   Timestamped:  ${path.join(REPORT_DIR, TIMESTAMP)}/`)
  console.log(`   Screenshots:  ${path.join(REPORT_DIR, 'latest', 'screenshots')}/`)
  
  console.log('\n🚀 Next Steps:')
  console.log('   1. Review the full report for details')
  console.log('   2. Check screenshots for visual issues')
  console.log('   3. Address P0 issues first')
  console.log('   4. Run audit again after fixes: npm run ui:audit')
  console.log('')
}

async function main() {
  const config = parseArgs()
  let server: ChildProcess | null = null
  
  try {
    log('LLMHive UI Audit Starting...')
    log(`Mode: ${config.mode}`)
    
    ensureDirectories()
    checkDependencies()
    
    server = startDevServer()
    
    runAuditTests(config)
    copyReportToTimestamped()
    printSummary()
    
  } catch (error) {
    log(`Audit failed: ${error}`, 'error')
    process.exit(1)
  } finally {
    if (server) {
      log('Shutting down development server...')
      process.kill(-server.pid!, 'SIGTERM')
    }
  }
}

main()

