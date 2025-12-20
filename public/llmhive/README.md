# LLMHive Background Assets

This folder contains the background images for the LLMHive global UI theme.

## Required Assets

Place the following high-resolution images in this folder:

1. **bg-mobile.png** - Background image for mobile devices (screens < 768px)
   - Optimized for portrait orientation
   - Features the LLMHive forest/nature theme with warm amber lighting

2. **bg-desktop.png** - Background image for desktop screens (screens >= 768px)
   - Optimized for landscape orientation
   - Complements the mobile version while utilizing wider aspect ratio

3. **logo.png** (optional) - High-resolution logo
   - Transparent PNG format recommended
   - The app already references `/logo.png` in the root public folder

## Image Guidelines

- Use high-resolution originals to ensure clarity on retina displays
- Images should have dark tones that work well with the glassmorphic overlay
- Avoid bright areas that might reduce text readability
- The overlay CSS automatically adds:
  - A warm orange glow at the top
  - A dark gradient at the bottom for text readability
  - A vignette effect to focus attention on content

## CSS Reference

The images are referenced in `/app/globals.css` under the `.llmhive-bg-image` class:

```css
.llmhive-bg-image {
  background-image: url("/llmhive/bg-mobile.png");
}

@media (min-width: 768px) {
  .llmhive-bg-image {
    background-image: url("/llmhive/bg-desktop.png");
  }
}
```

## Fallback

If images fail to load, the background will display a dark color (#050806) as defined in `.llmhive-bg-root`.

