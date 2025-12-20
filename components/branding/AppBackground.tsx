import React from "react";

/**
 * Global, fixed background for the entire app.
 * - Uses CSS (media queries) to swap mobile/desktop images at runtime.
 * - Layers multiple overlays for warmth, contrast, and vignette effect.
 * - Has pointer-events: none, so it won't block any UI interactions.
 * 
 * Required assets in public/llmhive/:
 * - bg-mobile.jpg (background image for mobile devices, < 768px)
 * - bg-desktop.jpg (background image for desktop screens, >= 768px)
 */
export default function AppBackground() {
  return (
    <div aria-hidden className="llmhive-bg-root">
      <div className="llmhive-bg-image" />
      <div className="llmhive-bg-overlay" />
      <div className="llmhive-bg-vignette" />
    </div>
  );
}

