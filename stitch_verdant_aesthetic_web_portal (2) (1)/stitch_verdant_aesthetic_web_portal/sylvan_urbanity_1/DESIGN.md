---
name: Sylvan Urbanity
colors:
  surface: '#faf9f6'
  surface-dim: '#dadad7'
  surface-bright: '#faf9f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f4f0'
  surface-container: '#eeeeea'
  surface-container-high: '#e8e8e5'
  surface-container-highest: '#e2e3df'
  on-surface: '#1a1c1a'
  on-surface-variant: '#424843'
  inverse-surface: '#2f312f'
  inverse-on-surface: '#f1f1ed'
  outline: '#727972'
  outline-variant: '#c2c8c0'
  surface-tint: '#466550'
  primary: '#163422'
  on-primary: '#ffffff'
  primary-container: '#2d4b37'
  on-primary-container: '#99baa1'
  inverse-primary: '#adcfb4'
  secondary: '#5f5f58'
  on-secondary: '#ffffff'
  secondary-container: '#e2e0d7'
  on-secondary-container: '#64635c'
  tertiary: '#1b341d'
  on-tertiary: '#ffffff'
  tertiary-container: '#314b32'
  on-tertiary-container: '#9dba9a'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c8ebd0'
  primary-fixed-dim: '#adcfb4'
  on-primary-fixed: '#022110'
  on-primary-fixed-variant: '#2f4d39'
  secondary-fixed: '#e5e2da'
  secondary-fixed-dim: '#c9c6be'
  on-secondary-fixed: '#1c1c17'
  on-secondary-fixed-variant: '#474741'
  tertiary-fixed: '#ccebc8'
  tertiary-fixed-dim: '#b0ceae'
  on-tertiary-fixed: '#07200b'
  on-tertiary-fixed-variant: '#334d34'
  background: '#faf9f6'
  on-background: '#1a1c1a'
  surface-variant: '#e2e3df'
typography:
  headline-display:
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
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
---

## Brand & Style

The design system is rooted in the "Sylvan Urbanity" narrative—a harmonious blend of organic nature and civic precision. It aims to evoke feelings of stability, ecological stewardship, and forward-thinking governance. The target audience includes residents, local business owners, and government officials who seek a seamless, high-trust digital interface for city interactions.

The visual style is **Corporate Modern** with **Glassmorphic** nuances. It utilizes heavy whitespace to suggest clarity of thought and purpose. To honor the natural reference, the system employs translucent "frosted" overlays that allow landscape photography to bleed through, softening the industrial nature of typical SaaS tools and making the "Smart City" feel like a "Green City."

## Colors

The palette is derived directly from the lush canopy and stony riverbeds of the reference landscape. 

- **Primary (Forest Green):** A deep, authoritative green used for primary actions, headers, and branding to establish trust.
- **Secondary (Warm Beige):** A soft, parchment-inspired neutral that replaces clinical whites, providing a more human and accessible backdrop.
- **Tertiary (Sage):** A mid-tone green for supportive elements like success states, icons, and secondary buttons.
- **Neutral (Charcoal Green):** A near-black with a hint of green for typography to maintain high contrast while remaining softer on the eyes than pure black.

Translucent tokens (`overlay_light` and `overlay_dark`) should be used for cards or panels sitting atop photography to ensure WCAG AA legibility while maintaining a sense of place.

## Typography

This design system uses **Manrope** as the primary typeface for its unique balance of geometric precision and humanist warmth. It feels modern and "smart" without being cold. 

- **Headlines:** Use a tighter letter spacing and heavier weights to create a sense of importance.
- **Body:** Set with generous line height (1.6) to ensure maximum readability for complex civic information.
- **Labels:** **Hanken Grotesk** is used for utility elements (tags, metadata, small buttons) to provide a crisp, technical contrast to the more fluid Manrope.
- **Scale:** On mobile devices, display headings should scale down aggressively to prevent awkward text wrapping, maintaining a maximum width of 90% of the viewport.

## Layout & Spacing

The layout follows a **Fluid Grid** model based on an 8px spacing system. 

- **Desktop:** 12-column grid with a 1280px max-width container. Central content should feel "airy" with large 64px side margins to focus the eye.
- **Tablet:** 8-column grid with 32px margins. 
- **Mobile:** 4-column grid with 16px margins. 

Spacing between sections (vertical rhythm) should be generous (80px–120px on desktop) to support the "serene" brand personality. Elements within a card should use tight spacing (16px–24px) to indicate relationship.

## Elevation & Depth

To maintain the "Smart City" professionalism, depth is created through **Tonal Layers** and **Backdrop Blurs** rather than heavy shadows.

- **Level 0 (Base):** Warm Beige surface.
- **Level 1 (Cards):** White or semi-transparent Beige surfaces with a very subtle, 1px low-contrast outline in Forest Green (at 10% opacity).
- **Level 2 (Floating/Modals):** Uses a soft ambient shadow (Color: Forest Green, Opacity: 5%, Blur: 20px, Offset-Y: 10px) to simulate a gentle lift.
- **The Glass Effect:** When components sit on imagery, use `backdrop-filter: blur(12px)` combined with the `overlay_light` token to create a premium, legible surface that feels integrated into the environment.

## Shapes

The shape language is **Rounded**, reflecting the organic curves found in nature (rivers, hills). 

Standard UI elements like buttons and input fields use a `0.5rem` (8px) radius. Larger containers, such as hero images or feature cards, should use `rounded-xl` (1.5rem / 24px) to create a soft, inviting frame. Avoid sharp corners to prevent the UI from feeling overly bureaucratic or "sharp."

## Components

- **Buttons:** Primary buttons are solid Forest Green with White Manrope text (Bold). Secondary buttons are outlined in Forest Green with a subtle Beige hover state.
- **Input Fields:** Use a solid White background with a 1px Beige-Dark border. On focus, the border transitions to Forest Green with a 2px outer glow (Soft Green).
- **Chips/Tags:** Use Hanken Grotesk. Success tags use a Sage background with Deep Green text; neutral tags use a light Beige background.
- **Cards:** Feature cards should have a subtle 1px border. When used for "City Projects," they may include a top-aligned image with the 24px corner radius applied only to the top.
- **Navigation:** The top bar should be persistent and utilize the Glassmorphic blur effect when the user scrolls, ensuring the brand colors stay visible against varying page content.
- **Status Indicators:** Use circular icons with soft color fills to indicate project status (e.g., "In Progress" is a soft Amber, "Completed" is Sage).