# 🎨 LLMHive Background Image Generation Prompts

**Purpose:** Generate improved, original background images for LLMHive that maintain the same aesthetic while avoiding copyright issues.

**Tool:** Nanobanana (or Midjourney/DALL-E 3)

**Date Created:** January 24, 2026

---

## 📍 Current Image Locations

| Version | Path | Current Resolution |
|---------|------|-------------------|
| Desktop | `public/llmhive/bg-desktop.png` | 1024 × 434 px |
| Mobile | `public/llmhive/bg-mobile.png` | 687 × 1024 px |

---

## 🖥️ Desktop Version Prompts

### Primary Prompt (Wide Panoramic - 21:9)

```
Ancient primeval forest at golden hour, massive towering sequoia and redwood tree trunks dominating the frame, warm amber sunset light filtering through the canopy creating ethereal god rays and atmospheric mist, lush emerald green fern carpet covering the forest floor, deep forest depth with layers of trees fading into the misty background, rich warm color palette of burnt orange, deep amber, forest green and chocolate brown bark textures, magical dreamlike atmosphere, volumetric lighting, cinematic composition, ultra-wide panoramic aspect ratio 21:9, photorealistic yet painterly quality, soft diffused light, peaceful serene mood, high detail bark textures, no people or animals, nature sanctuary ambiance

--ar 21:9 --style raw --v 6.1 --q 2
```

### Alternative Desktop Prompt

```
Enchanted old-growth forest panorama during magic hour, colossal redwood sentinels with deeply furrowed bark standing in morning mist, soft diffused sunlight creating luminous rays through the fog, carpet of sword ferns and oxalis covering the forest floor, layers of evergreen trees creating depth, warm amber and copper tones blending with deep forest greens, mystical tranquil atmosphere, professional landscape photography style, ultra-wide cinematic aspect ratio, 8K quality, sharp foreground with soft dreamy background bokeh, natural cathedral of trees

--ar 21:9 --style raw --v 6.1 --q 2 --s 250
```

### Desktop Prompt (16:9 Standard)

```
Majestic ancient redwood forest at sunset, towering sequoia tree trunks with rich textured bark, warm golden hour lighting with visible sun rays piercing through atmospheric mist, verdant fern-covered forest floor, deep perspective with trees layering into foggy distance, warm amber orange and forest green color palette, ethereal magical mood, cinematic wide shot, photorealistic quality, volumetric god rays, peaceful sanctuary atmosphere, no people, professional landscape photography

--ar 16:9 --style raw --v 6.1 --q 2
```

---

## 📱 Mobile Version Prompts

### Primary Prompt (Portrait - 9:16)

```
Majestic ancient forest grove vertical composition, towering giant sequoia trunks framing the scene on left and right, warm golden sunset glow visible through the tree canopy at top, soft atmospheric mist floating between the trees, ethereal light rays streaming down through the forest, verdant fern undergrowth in the foreground, rich textured bark on ancient tree trunks with warm orange light catching the edges, deep forest receding into misty background, dreamy magical atmosphere, warm amber and forest green color harmony, volumetric fog, cinematic portrait orientation, photorealistic with painterly softness, peaceful and majestic mood, high detail, no people or animals, sacred grove feeling

--ar 9:16 --style raw --v 6.1 --q 2
```

### Alternative Mobile Prompt

```
Vertical forest cathedral scene, ancient giant sequoia grove at sunrise, warm golden light illuminating the mist between towering tree columns, rich amber sky visible through the canopy, lush undergrowth of ferns glowing in the morning light, massive textured bark trunks creating natural framing, ethereal atmosphere with visible light beams, deep perspective looking into the endless forest, warm earth tones with pops of vibrant green, magical realism style, portrait composition optimized for mobile, cinematic color grading, peaceful meditative mood

--ar 9:16 --style raw --v 6.1 --q 2 --s 250
```

---

## 🎯 Key Style Elements to Maintain

| Element | Description |
|---------|-------------|
| **Trees** | Ancient sequoia/redwood with massive, deeply textured trunks |
| **Lighting** | Golden hour, warm amber/orange, god rays through mist |
| **Atmosphere** | Ethereal fog/mist creating depth and mystery |
| **Color Palette** | Warm: amber, burnt orange, sienna, chocolate brown, forest green |
| **Forest Floor** | Lush fern carpet, earthy tones, natural debris |
| **Mood** | Peaceful, magical, sanctuary-like, meditative |
| **Depth** | Multiple layers of trees fading into misty background |
| **Composition** | Trees framing the scene, central clearing with light |

---

## 📐 Recommended Output Resolutions

### Desktop Versions

| Resolution | Aspect Ratio | Use Case |
|------------|--------------|----------|
| **3840 × 1600** | 21:9 | Ultrawide monitors, hero sections |
| **2560 × 1080** | 21:9 | Standard ultrawide |
| **3840 × 2160** | 16:9 | 4K displays |
| **2560 × 1440** | 16:9 | QHD displays |
| **1920 × 1080** | 16:9 | Full HD fallback |

### Mobile Versions

| Resolution | Aspect Ratio | Use Case |
|------------|--------------|----------|
| **1440 × 2560** | 9:16 | High-end mobile (2K) |
| **1080 × 1920** | 9:16 | Standard mobile (1080p) |
| **1284 × 2778** | ~9:19.5 | iPhone 14 Pro Max |
| **1170 × 2532** | ~9:19.5 | iPhone 14/13 Pro |

---

## 🔧 Nanobanana-Specific Parameters

```
--ar [aspect ratio]    # 21:9, 16:9, 9:16, etc.
--style raw            # More photorealistic output
--v 6.1                # Latest version
--q 2                  # Highest quality
--s 250                # Higher stylization (optional)
--no [element]         # Exclude specific elements
```

---

## ✅ Copyright Safety Measures

These prompts ensure originality by:

1. ✅ **Generic descriptions** - Describing scene elements, not copying specific arrangements
2. ✅ **Different compositions** - Requesting varied tree placements and perspectives
3. ✅ **AI generation** - Each output is mathematically unique
4. ✅ **Style modifiers** - Adding variation through parameter adjustments
5. ✅ **Multiple alternatives** - Providing options to choose the best original result

---

## 📝 Post-Generation Checklist

After generating new images:

- [ ] Generate multiple variations (at least 4-6 per version)
- [ ] Select the best that matches the LLMHive aesthetic
- [ ] Upscale to maximum resolution
- [ ] Optimize file size for web (compress PNG/WebP)
- [ ] Test on actual website with text overlays
- [ ] Ensure sufficient contrast for readable text
- [ ] Replace files in `public/llmhive/` directory
- [ ] Test on multiple devices (desktop, tablet, mobile)
- [ ] Verify loading performance

---

## 🎨 Color Reference (Hex Values)

Based on the current images, target these colors:

| Color | Hex | Usage |
|-------|-----|-------|
| Warm Amber | `#E8A44C` | Sky, light rays |
| Sunset Orange | `#D4703A` | Sky gradient, bark highlights |
| Forest Green | `#3D5E3A` | Ferns, foliage |
| Deep Green | `#2A4428` | Shadow areas, depth |
| Bark Brown | `#5C3D2E` | Tree trunks |
| Mist White | `#E8E4D8` | Atmospheric fog |

---

## 📁 File Naming Convention

When saving new images:

```
bg-desktop-v2.png       # New desktop version
bg-mobile-v2.png        # New mobile version
bg-desktop-4k.png       # 4K resolution variant
bg-mobile-2k.png        # 2K resolution variant
```

---

*Last Updated: January 24, 2026*
