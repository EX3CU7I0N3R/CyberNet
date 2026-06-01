---
name: Tactical Deep Space System
colors:
  surface: '#0d1516'
  surface-dim: '#0d1516'
  surface-bright: '#333a3c'
  surface-container-lowest: '#080f11'
  surface-container-low: '#151d1e'
  surface-container: '#192122'
  surface-container-high: '#242b2d'
  surface-container-highest: '#2e3638'
  on-surface: '#dce4e5'
  on-surface-variant: '#bac9cc'
  inverse-surface: '#dce4e5'
  inverse-on-surface: '#2a3233'
  outline: '#849396'
  outline-variant: '#3b494c'
  surface-tint: '#00daf3'
  primary: '#c3f5ff'
  on-primary: '#00363d'
  primary-container: '#00e5ff'
  on-primary-container: '#00626e'
  inverse-primary: '#006875'
  secondary: '#c2c6d1'
  on-secondary: '#2c3139'
  secondary-container: '#474c54'
  on-secondary-container: '#b7bcc6'
  tertiary: '#ffeac0'
  on-tertiary: '#3e2e00'
  tertiary-container: '#fec931'
  on-tertiary-container: '#6f5500'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#9cf0ff'
  primary-fixed-dim: '#00daf3'
  on-primary-fixed: '#001f24'
  on-primary-fixed-variant: '#004f58'
  secondary-fixed: '#dee2ed'
  secondary-fixed-dim: '#c2c6d1'
  on-secondary-fixed: '#171c23'
  on-secondary-fixed-variant: '#42474f'
  tertiary-fixed: '#ffdf96'
  tertiary-fixed-dim: '#f3bf26'
  on-tertiary-fixed: '#251a00'
  on-tertiary-fixed-variant: '#594400'
  background: '#0d1516'
  on-background: '#dce4e5'
  surface-variant: '#2e3638'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-md:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: 0.02em
  body-lg:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Space Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-caps:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.1em
  mono-data:
    fontFamily: Space Grotesk
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 20px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style

The design system is engineered for high-stakes aerospace environments, evoking a sense of "Cinematic Realism" within a futuristic military framework. It balances high-fidelity aesthetics with tactical utility, ensuring that critical information is prioritized while maintaining an immersive, atmospheric experience.

The visual style is a hybrid of **Glassmorphism** and **Modern Corporate**, enhanced by environmental effects such as depth fog, subtle scanlines, and bloom. Every element should feel like a projection or a physical glass panel within a spacecraft's bridge. The emotional response is one of precision, technological superiority, and urgent focus.

## Colors

This design system utilizes a "Deep Space" palette characterized by high-luminosity accents against an abyssal background.

- **Background (#05070A):** The void. Used for the lowest layer of the interface.
- **Surface/Panel (#0A0F16):** The structural "Tactical Slate." These panels should utilize subtle translucency (85-95% opacity) to allow background textures or depth fog to bleed through.
- **Accent (#00E5FF):** "Cyber Cyan." This is the primary interactive and branding color, often accompanied by a soft glow/bloom effect.
- **Semantic Colors:** Green, Amber, and Red are reserved for status indicators (Success, Warning, and Danger) and must maintain high saturation to ensure legibility against dark surfaces.

## Typography

The design system exclusively uses **Space Grotesk** for its technical, geometric characteristics that reflect modern aerospace engineering.

Headlines should be bold and tightly spaced to feel authoritative. Labels and data points utilize uppercase transformations and increased letter spacing to mimic military technical readouts. For data-heavy tactical displays, smaller sizes are preferred but must remain high-contrast (Cyber Cyan or White) to ensure readability in simulated low-light environments.

## Layout & Spacing

This design system employs a **Modular Fixed Grid** philosophy, reminiscent of a Head-Up Display (HUD). 

- **Desktop:** A 12-column grid with a fixed 1440px max-width container, centered on the screen. Outer margins are generous (48px) to simulate a "bezel" effect.
- **Tablet:** An 8-column fluid grid with 24px margins.
- **Mobile:** A 4-column fluid grid with 16px margins.

Spacing follows a 4px base unit to ensure alignment with technical data modules. Components are often grouped into "Control Blocks" using consistent 24px (md) gaps.

## Elevation & Depth

Visual hierarchy in the design system is achieved through **Glassmorphism and Bloom** rather than traditional drop shadows.

- **Layer 0 (Background):** #05070A with a faint, static scanline overlay (2% opacity) and occasional "depth fog" (radial gradients of #0A0F16).
- **Layer 1 (Panels):** #0A0F16 at 90% opacity with a `16px` backdrop blur. Borders should be 1px solid semi-transparent Cyan or Slate.
- **Layer 2 (Floating/Active):** Elements that are active or require immediate attention use a **Glow/Bloom** effect. This is achieved by a 1px border of #00E5FF and a matching outer shadow with a large spread and low opacity (e.g., `box-shadow: 0 0 15px rgba(0, 229, 255, 0.3)`).
- **Interactivity:** Hover states should trigger a "flicker" or brightness increase, simulating a light-based projection.

## Shapes

The shape language is defined by **Precision**. While a standard `0.5rem` (8px) radius is used for primary containers to ensure a modern feel, interactive elements often lean towards "Sharp-Minimal."

- **Containers/Panels:** Use `rounded-lg` (16px) for major structural sections to create a "cockpit window" aesthetic.
- **Buttons/Inputs:** Use the base `0.5rem` (8px) roundedness.
- **Data Points:** Small status chips and badges may use `rounded-xl` or pill shapes to distinguish them from structural UI elements.

## Components

### Buttons
Primary buttons are solid Cyber Cyan with black text. Secondary buttons are "Ghost" style with a 1px Cyan border and a subtle background glow on hover. High-intensity actions (Danger) use Critical Red with a 2px outer bloom.

### Input Fields
Inputs are styled as "underlined" or "bracketed" fields. Avoid full boxes where possible. Use a semi-transparent Slate background and a bright Cyan cursor. Labels should always be in `label-caps` style above the field.

### Cards & Panels
Never use flat, solid-color cards. Every panel must have a 1px border (either #0A0F16 or semi-transparent Cyan) and use backdrop blur. Corner "brackets" or "crosshair" ornaments at the edges of panels add to the tactical aerospace aesthetic.

### Status Indicators
Use circular "LED" icons with a heavy inner-glow (Success, Warning, Danger). These should pulse slowly when in a critical state.

### Lists & Data Grids
Rows should be separated by thin, low-opacity lines. Data density should be high, using the `mono-data` typography role for numerical values to ensure vertical alignment.