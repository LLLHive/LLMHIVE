# LLMHive UI Audit Tool

Comprehensive automated UI testing and auditing for LLMHive.

## Overview

The UI Audit tool performs:
- **Route Discovery**: Crawls all app routes and validates they load correctly
- **OpenRouter Validation**: Verifies rankings and categories match API data
- **Click Crawler**: Safely clicks through interactive elements
- **Error Detection**: Captures console errors and network failures
- **Accessibility Checks**: Basic a11y validation

## Quick Start

```bash
# Run full UI audit
npm run ui:audit

# Run quick smoke test
npm run ui:audit:quick

# Run with visible browser
npm run ui:audit:headed
```

## What Gets Audited

### A) Models / Rankings UI
- Category list completeness (including nested like marketing/seo)
- Top 10 rankings order matches API
- Timestamp/"as of" indicators render
- Provider logos render for each model row

### B) Chat UI  
- Model dropdown category list matches Models page
- Category/model selection populates requests correctly
- Clarifying question flow works

### C) Navigation & Global UX
- No console errors
- No unhandled promise rejections  
- No 4xx/5xx on key routes
- Basic a11y checks

## Mock Mode

The audit runs in **deterministic mock mode** by default:
- No external API calls required
- Uses fixtures from `tests/fixtures/openrouter/`
- Consistent results across runs

To run with live APIs (optional):
```bash
LIVE_APIS=true npm run ui:audit
```

## Reports

Reports are generated in `docs/ui_audit/reports/`:

```
docs/ui_audit/reports/
├── latest/
│   ├── report.md          # Main audit report
│   ├── issues.json        # Machine-readable issues
│   └── screenshots/       # Page and click screenshots
└── 2025-12-19T10-30-00/   # Timestamped archive
    ├── report.md
    ├── issues.json
    └── screenshots/
```

### Report Format

Each issue includes:
- **Severity**: P0 (critical), P1 (high), P2 (medium)
- **Type**: console_error, network_error, correctness, accessibility, ux
- **Description**: What's wrong
- **Repro Steps**: How to reproduce
- **Suspected Files**: Where to fix
- **Suggested Fix**: How to fix

## Safety Features

The click crawler has built-in safety:

### Skip Destructive Elements
Elements with these keywords are never clicked:
- delete, remove, logout, sign out, reset
- clear, drop, billing, pay, subscribe, revoke
- disconnect, unlink, destroy, terminate
- sync now (avoids mutating prod data)

### Skip External Links
Links to external domains are skipped:
- openrouter.ai, github.com, google.com
- vercel.com, anthropic.com, openai.com

### Click Limits
- Max 40 clicks per page
- Visited elements are tracked to avoid loops
- Dialogs/modals are auto-closed

## E2E Tests

The audit includes reusable E2E tests:

```typescript
// Test category completeness
test('Models page: Category list is complete')

// Test rankings order
test('Models page: Top 10 rankings match API order')

// Test chat integration  
test('Chat page: Model dropdown has categories')

// Test clarifying questions
test('Chat page: Clarifying questions flow works')
```

Run specific tests:
```bash
npm run test:e2e -- tests/e2e/audit/ui-audit.spec.ts -g "category"
```

## CI Integration

Add to your CI pipeline:

```yaml
# GitHub Actions example
- name: UI Audit
  run: |
    npm ci
    npm run ui:audit:quick
    
- name: Upload Audit Report
  uses: actions/upload-artifact@v3
  with:
    name: ui-audit-report
    path: docs/ui_audit/reports/latest/
```

## Extending the Audit

### Add New Routes

Edit `ROUTES_TO_AUDIT` in `tests/e2e/audit/ui-audit.spec.ts`:

```typescript
const ROUTES_TO_AUDIT = [
  { path: '/', name: 'Home' },
  { path: '/new-route', name: 'New Feature' },
  // ...
]
```

### Add New Mock Data

Edit `tests/e2e/audit/openrouter-mock.ts`:

```typescript
export const MOCK_CATEGORIES = {
  // Add new categories
}

export const MOCK_RANKINGS = {
  // Add new ranking data
}
```

### Add New Validation

Add new test blocks in `ui-audit.spec.ts`:

```typescript
test.describe('UI Audit - New Feature', () => {
  test('New validation', async ({ page }) => {
    // Your validation logic
  })
})
```

## Troubleshooting

### Tests timeout
- Increase `timeout` in `playwright.config.ts`
- Check if dev server is starting properly

### Mock data not loading
- Verify `setupOpenRouterMocks()` is called in `beforeEach`
- Check route patterns match actual API routes

### Screenshots not capturing
- Ensure `docs/ui_audit/reports/latest/screenshots/` exists
- Check file permissions

## Files

```
tests/e2e/audit/
├── ui-audit.spec.ts      # Main audit tests
├── openrouter-mock.ts    # API mock data

scripts/
├── ui-audit.ts           # Audit runner script

docs/ui_audit/
├── README.md             # This file
└── reports/              # Generated reports
```

