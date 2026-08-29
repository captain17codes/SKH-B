---
name: Nocturnal Sylvan
colors:
  surface: '#121412'
  surface-dim: '#121412'
  surface-bright: '#383a37'
  surface-container-lowest: '#0d0f0d'
  surface-container-low: '#1a1c1a'
  surface-container: '#242e28'
  surface-container-high: '#292a28'
  surface-container-highest: '#343533'
  on-surface: '#e3e3df'
  on-surface-variant: '#c2c8c0'
  inverse-surface: '#e3e3df'
  inverse-on-surface: '#2f312f'
  outline: '#8c928b'
  outline-variant: '#424843'
  surface-tint: '#adcfb4'
  primary: '#adcfb4'
  on-primary: '#183624'
  primary-container: '#2d4b37'
  on-primary-container: '#99baa1'
  inverse-primary: '#466550'
  secondary: '#bec9c0'
  on-secondary: '#28332c'
  secondary-container: '#414c45'
  on-secondary-container: '#b0bbb2'
  tertiary: '#efb9be'
  on-tertiary: '#49262b'
  tertiary-container: '#613a3f'
  on-tertiary-container: '#daa5ab'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c8ebd0'
  primary-fixed-dim: '#adcfb4'
  on-primary-fixed: '#022110'
  on-primary-fixed-variant: '#2f4d39'
  secondary-fixed: '#dae5dc'
  secondary-fixed-dim: '#bec9c0'
  on-secondary-fixed: '#141e18'
  on-secondary-fixed-variant: '#3f4942'
  tertiary-fixed: '#ffd9dc'
  tertiary-fixed-dim: '#efb9be'
  on-tertiary-fixed: '#311217'
  on-tertiary-fixed-variant: '#633c41'
  background: '#121412'
  on-background: '#e3e3df'
  surface-variant: '#343533'
  surface-main: '#1a241e'
  surface-elevated: '#2d3831'
  text-headline: '#ffffff'
  text-body: '#e0e0e0'
  status-success: '#76d68f'
  status-warning: '#ffd54f'
  status-error: '#ff8a80'
typography:
  display:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-sm:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
  max-width: 1280px
---

## Brand & Style
This design system is a high-contrast, dark-mode evolution of the Sylvan narrative, transitioning from a sunlit forest to a nocturnal, "Midnight City" aesthetic. It maintains the core values of ecological stewardship and civic precision but shifts the emotional response toward focus, prestige, and high-tech efficiency. The target audience remains residents and officials, now provided with a low-strain, high-visibility interface optimized for deep-focus tasks and evening use.

The visual style is **Corporate Modern** with **Minimalist** execution. Unlike its predecessor, this version moves away from glassmorphism and translucency in favor of solid, high-contrast surfaces and crisp definition. By removing blurs and utilizing a deep charcoal-green foundation, the UI achieves a "command center" feel—authoritative, reliable, and exceptionally clear.

## Colors
The palette is recalibrated for high-contrast legibility against a deep forest-charcoal base.

- **Primary Surface:** `#1a241e` (Forest Charcoal) serves as the base for the entire application, providing a restful but distinctly "green" dark mode.
- **Secondary Surfaces:** Tiered forest tones (`#242e28` and `#2d3831`) create hierarchy through lightness rather than shadows.
- **Accent (Forest Green):** The primary brand green (`#2d4b37`) is used for key action buttons and active states, optimized here for luminosity against dark backgrounds.
- **Typography:** Pure White (`#ffffff`) is reserved for headlines to ensure maximum impact, while Body Text uses a high-contrast Off-White (`#e0e0e0`) to reduce eye strain while maintaining accessibility.
- **Status Colors:** Success, Warning, and Error colors are desaturated and brightened to prevent "vibration" against the dark green surfaces while remaining instantly recognizable.

## Typography
The typography leverages **Manrope** for its technical yet warm character. In this high-contrast dark mode, font weights are slightly preserved to avoid the "thinning" effect often seen on dark backgrounds.

- **Headlines:** Set in Pure White. The tighter letter spacing in `display` roles creates a bold, architectural feel.
- **Body:** Set in Off-White (`#e0e0e0`) with a generous 1.6 line-height. This ensures that long-form civic data remains legible without causing glare.
- **Labels:** **Hanken Grotesk** is used for all utility and metadata roles. Its high x-height and geometric clarity make it ideal for small-scale technical information.

## Layout & Spacing
The layout uses a **Fluid Grid** model with a disciplined 8px rhythmic increment.

- **Desktop (1240px+):** A 12-column grid with 64px margins. The extra-wide margins create a "gallery" effect, centering focus on the content.
- **Tablet:** An 8-column grid with 32px margins.
- **Mobile:** A 4-column grid with 16px margins.

Vertical rhythm is intentionally expansive. Sections should be separated by 80px to 120px to prevent the dark interface from feeling cramped or overwhelming. Use the 8px unit for all internal component padding to maintain structural harmony.

## Elevation & Depth
In this design system, depth is strictly functional and avoids all blur or transparency effects. 

- **Tonal Layering:** Hierarchy is achieved by stepping up the lightness of the surface color. The background is the darkest (`#1a241e`), cards sit on the next tier (`#242e28`), and interactive elements or floating menus sit on the highest tier (`#2d3831`).
- **Low-Contrast Outlines:** Instead of shadows, components are defined by 1px solid borders. For cards, use a subtle `#ffffff` at 10% opacity. For active inputs or primary focus states, use the primary Forest Green.
- **No Blurs:** All surfaces are 100% opaque. This ensures maximum rendering performance and absolute clarity for information-dense layouts.

## Shapes
The shape language is **Rounded**, providing a necessary organic counterpoint to the high-contrast, technical color palette.

- **Standard Elements:** Buttons, inputs, and small chips use a `0.5rem` (8px) radius.
- **Large Containers:** Hero sections and main content cards use `rounded-xl` (1.5rem) to soften the screen's edges.
- **Selection Indicators:** Use pill-shaped (full radius) treatments for toggle switches and active navigation indicators to provide clear visual distinction from square-format content.

## Components
- **Buttons:** Primary buttons are solid Forest Green (`#2d4b37`) with Pure White text. Secondary buttons use a thick 2px outline of the same green with no fill.
- **Input Fields:** Surfaces use the `#242e28` container color with a 1px border. Upon focus, the border turns Pure White to provide an unmistakable "active" signal.
- **Chips/Tags:** Status tags use the adjusted status colors (Success/Warning/Error) as small leading dots or thin borders rather than full-color fills to maintain the dark-mode aesthetic.
- **Lists:** Data rows should be separated by 1px solid dividers using `#ffffff` at 5% opacity.
- **Cards:** Cards are solid blocks of `#242e28`. They do not use shadows; instead, they are distinguished from the background solely by their lighter tonal value and subtle 1px border.
- **Navigation:** The sidebar or top-nav should use the darkest surface (`#1a241e`) to recede, allowing the content area (on `#242e28`) to feel like the primary layer of focus.