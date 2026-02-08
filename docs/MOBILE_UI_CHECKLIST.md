# Mobile UI QA Checklist

Use this list before mobile releases to keep the chat experience world-class.

## Chat Input
- Textarea padding leaves room for all action buttons on 320px width.
- Action buttons remain fully visible with the keyboard open.
- Safe-area inset is respected on iPhone devices.
- Long prompts scroll inside the input without clipping.

## Header Controls
- Toolbar controls are reachable on small screens via the "Controls" toggle.
- Dropdowns open without horizontal overflow.
- Header remains readable with Dynamic Type and 200% zoom.

## Scrolling & Layout
- No horizontal scrolling on iPhone Safari and Android Chrome.
- Sticky header does not overlap the first message.
- Message list scrolls independently of the header and input.

## Media & Attachments
- Attachment chips wrap without pushing buttons off-screen.
- Image previews scale to viewport width.

## Regression Checks
- Test on iPhone 12/13/14, Pixel 7, and small Android (360px).
- Test Safari and Chrome with the keyboard open.
