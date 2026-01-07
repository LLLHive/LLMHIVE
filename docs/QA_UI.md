# UI Regression Checklist

> **Purpose**: Manual checklist for UI quality validation before releases.
> Run through this checklist in both **mobile (390px viewport)** and **desktop (1440px)**.

## 🎨 Background & Theming

### Forest Background
- [ ] Forest background image visible on mobile (`/llmhive/bg-mobile.png`)
- [ ] Forest background image visible on desktop (`/llmhive/bg-desktop.png`)
- [ ] Background visible through sidebar (glass effect, not opaque)
- [ ] Background visible through main content area
- [ ] No solid black/dark overlays hiding the background
- [ ] Background images return HTTP 200 (check Network tab in DevTools)

### Theme Consistency  
- [ ] Dark mode properly applied
- [ ] Bronze/gold accent colors consistent (#cd7f32)
- [ ] Text is readable against all backgrounds
- [ ] Glassmorphism blur effects working on sidebar and panels

## 📱 Sidebar (Mobile-First)

### Chat Items
- [ ] 3-dot menu button visible on mobile WITHOUT hovering
- [ ] 3-dot menu button appears on desktop hover AND keyboard focus
- [ ] 3-dot menu opens and all options are clickable
- [ ] Chat item highlight has fully rounded corners (pill shape)
- [ ] Active/selected chat has bronze accent ring
- [ ] No clipping of rounded corners at sidebar edge
- [ ] Chat titles truncate properly with ellipsis

### Project Items
- [ ] 3-dot menu button visible on mobile
- [ ] Project expand/collapse chevrons visible
- [ ] Nested chat items properly indented

### Navigation
- [ ] Sidebar collapse/expand toggle works
- [ ] All sidebar links navigate correctly
- [ ] Search input appears and functions
- [ ] "Collaborate" section links to Settings

## 🗣️ Chat Area

### Messages
- [ ] User messages align right, AI messages align left
- [ ] AI avatar/badge displays correctly
- [ ] Loading dots animate while waiting for response
- [ ] Auto-scroll works (scrolls to new messages)
- [ ] User scroll lock works (doesn't fight user scroll)

### Input Area
- [ ] Input textarea visible and focusable
- [ ] Send button works (click and Enter key)
- [ ] Attachment buttons visible and functional
- [ ] Voice input button works (if enabled)

### Error States
- [ ] Network errors show clear message
- [ ] 403 (plan limit) shows upgrade CTA
- [ ] Clarification prompts display distinctly

## 🎯 Home Screen

### Hero Section
- [ ] 3D logo visible and not clipped
- [ ] Title and subtitle readable
- [ ] Template cards visible

### Template Cards
- [ ] All template cards visible
- [ ] Click/tap opens configuration drawer
- [ ] Drawer slides in smoothly

## ⚙️ Settings & Modals

### Modals
- [ ] All dialog/modal backgrounds have proper backdrop
- [ ] Modal close buttons (X) work
- [ ] Escape key closes modals
- [ ] Focus trap works within modals

### Forms
- [ ] All inputs have visible borders/focus states
- [ ] Buttons have proper hover states
- [ ] Form validation errors display clearly

## 🔐 Authentication (Clerk)

### Social Buttons
- [ ] Google, Apple, Facebook buttons visible in row
- [ ] Apple logo appears white on dark background
- [ ] All social buttons clickable
- [ ] "Last used" label is hidden

### Forms
- [ ] Password visibility toggle (eye icon) is white
- [ ] OTP input boxes have orange border
- [ ] All Clerk styling consistent with dark theme

---

## Quick Verification Commands

```bash
# Start dev server
npm run dev

# Check if background images exist and are accessible
curl -I http://localhost:3000/llmhive/bg-mobile.png
curl -I http://localhost:3000/llmhive/bg-desktop.png

# Run e2e tests (if configured)
npm run test:e2e
```

## Common Regression Causes

1. **Background hidden**: z-index stacking, opaque wrappers, CSS overrides
2. **3-dot menu invisible on mobile**: `opacity-0` without responsive fallback
3. **Clipped corners**: `overflow-hidden` on parent containers
4. **Social buttons issues**: Overly broad CSS selectors

---

*Last updated: 2026-01-07*

