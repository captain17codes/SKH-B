---
name: Sylvan Urbanity
colors:
  surface: '#fbf9f8'
  surface-dim: '#dbd9d9'
  surface-bright: '#fbf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#eae8e7'
  surface-container-highest: '#e4e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#424844'
  inverse-surface: '#303030'
  inverse-on-surface: '#f2f0f0'
  outline: '#727973'
  outline-variant: '#c2c8c2'
  surface-tint: '#496455'
  primary: '#173124'
  on-primary: '#ffffff'
  primary-container: '#2d4739'
  on-primary-container: '#98b5a3'
  inverse-primary: '#b0cdbb'
  secondary: '#5f5e5b'
  on-secondary: '#ffffff'
  secondary-container: '#e5e2dd'
  on-secondary-container: '#656461'
  tertiary: '#012e49'
  on-tertiary: '#ffffff'
  tertiary-container: '#204561'
  on-tertiary-container: '#8fb2d2'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ccead6'
  primary-fixed-dim: '#b0cdbb'
  on-primary-fixed: '#062014'
  on-primary-fixed-variant: '#324c3e'
  secondary-fixed: '#e5e2dd'
  secondary-fixed-dim: '#c9c6c2'
  on-secondary-fixed: '#1c1c19'
  on-secondary-fixed-variant: '#474743'
  tertiary-fixed: '#cce5ff'
  tertiary-fixed-dim: '#a7caec'
  on-tertiary-fixed: '#001e31'
  on-tertiary-fixed-variant: '#254a66'
  background: '#fbf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e2'
typography:
  display:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1200px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
  stack-sm: 12px
  stack-md: 24px
  stack-lg: 48px
---

## Brand & Style
The brand personality is rooted in "Sylvan Urbanity"—a blend of organic serenity and metropolitan precision. It is designed to evoke a sense of grounded stability, particularly during technical friction points like error states or fallbacks. The target audience values sophistication and clarity, preferring a reassuring partner over an alarming system.

The design style is **Modern Minimalism** with a **Tactile** edge. It utilizes generous whitespace, high-contrast accessible typography, and subtle layered surfaces to create a UI that feels architectural yet human. By replacing aggressive error patterns with soft, intentional cooling tones, the system maintains user trust even when the product fails.

## Colors
The palette is dominated by "Deep Forest" (Primary) and "Stone Linen" (Secondary/Background). This combination provides a high-contrast, sophisticated foundation that feels natural rather than clinical.

To handle errors and outages without triggering anxiety:
- **Error/Outage States:** Use muted blues and slate grays (`#7D8C97`) instead of red. This "cool-down" effect signals a technical pause rather than a critical failure.
- **Information/Alerts:** Utilize a warm amber (`#D9A05B`) for warnings to maintain a soft, legible glow that stands out against the green and beige.
- **Success:** A lighter variant of the forest green ensures feedback feels integrated into the brand's core DNA.

## Typography
This design system utilizes **Manrope** across all levels to maintain a clean, geometric, yet friendly appearance. The typeface was chosen for its excellent legibility at small sizes and its modern, open counters which prevent the UI from feeling claustrophobic during data-heavy or error-prone moments.

- **Headlines:** Use tight letter-spacing and semi-bold weights to anchor the page.
- **Body Text:** Maintains a generous line height (1.5x) to ensure readability for elderly or vision-impaired users, adhering to high-contrast accessibility standards.
- **Labels:** Uppercase is permitted for small labels (`label-sm`) to create a clear visual hierarchy between metadata and primary content.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy for desktop (centered 12-column) and a **Fluid Grid** for mobile. A strict 8px rhythmic scale is applied to all padding and margins to ensure a predictable visual cadence.

- **Mobile:** 4-column layout with 16px side margins.
- **Desktop:** 12-column layout with a 1200px max-width container to prevent line-lengths from becoming unreadable.
- **Error States:** Use "Optical Centering"—positioning error messages slightly above the geometric center of the viewport to create a more balanced, intentional feel. 
- **White Space:** Increase vertical stacking (`stack-lg`) around error illustrations to allow the UI to "breathe" and reduce user frustration.

## Elevation & Depth
Depth is conveyed through **Tonal Layers** and **Ambient Shadows**. This avoids the harshness of high-contrast borders in favor of soft, structural separation.

- **Surface Levels:** The base background is the beige Stone Linen. Content cards use a pure white or a slightly lighter tint of the background to appear "raised."
- **Shadows:** Use extremely diffused, low-opacity shadows (10% opacity) with a slight green or blue tint (`#2D4739` for standard, `#7D8C97` for error states) to ground elements in the environment.
- **Interactivity:** On hover, elements should decrease their shadow spread and slightly shift in Y-offset to simulate a physical press.

## Shapes
The shape language is **Rounded**, avoiding the clinical feel of sharp corners or the "juvenile" feel of full pills. 

- **Primary Elements:** Buttons and input fields use a 0.5rem (8px) radius.
- **Containers:** Large cards and modals use 1rem (16px) for a softer, more architectural silhouette.
- **Icons:** Use a consistent 2px stroke weight with rounded caps and joins to match the typography's terminal endings.

## Components
- **Buttons:** The primary button is Deep Forest green with white text. Secondary buttons use a transparent background with a 1.5px Forest Green border.
- **Input Fields:** Use a subtle Stone Linen fill with a bottom-border only in the default state, shifting to a full-border outline on focus for accessibility.
- **Error State Messaging:** Avoid "X" marks. Use "Refresh" or "Return" as primary actions. Error illustrations should be abstract and geometric, utilizing the muted blue palette.
- **Chips/Badges:** For status indicators, use low-saturation background tints with high-saturation text of the same hue (e.g., Soft Blue background with Slate Blue text for "System Offline").
- **Cards:** Cards should be borderless, relying on the 1rem rounded corners and ambient shadows for definition.
- **Progress Bars:** Use a continuous, smooth animation rather than "stepped" blocks to convey a calm, flowing sense of progress during fallbacks.