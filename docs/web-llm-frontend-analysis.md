# web-llm-chat Frontend — Visual System and Architecture

This document analyzes the frontend under `aimhi-chatbot/web-llm-chat-main` (Next.js + SCSS), focusing on color tokens, typography, component styling, and the layout system so we can port its look & feel to our Flask app.

## Tech Stack

- Framework: Next.js 13+ (App Router)
- Styling: SCSS modules + global CSS variables; component-level `.module.scss`
- Fonts: Noto Sans (self-hosted in `public/fonts` via `public/fonts/font.css`)
- Icons: Inline SVGs in `app/icons/*.svg`
- Themes: Light/Dark via CSS variables (`.light`/`.dark` classes and `@media (prefers-color-scheme: dark)`) defined in `app/styles/globals.scss`

## Color System (CSS Variables)

Defined in `app/styles/globals.scss` via two mixins. Key tokens below.

Light theme
- `--white: #ffffff` — surface
- `--black: rgb(48, 48, 48)` — primary text
- `--gray: rgb(240, 240, 240)` — page background
- `--light-gray: rgb(120, 120, 120)` — secondary text
- `--primary: rgb(90, 96, 135)` — brand/selection accent (muted blue)
- `--second: rgb(228, 229, 241)` — sidebar/secondary bg (periwinkle)
- `--hover-color: #f3f3f3`
- `--bar-color: rgba(0, 0, 0, 0.1)` — hairlines
- `--mlc-icon-color: rgb(6, 37, 120)` — icon emphasis
- Shadows/borders:
  - `--shadow: 50px 50px 100px 10px rgba(0,0,0,0.1)`
  - `--card-shadow: 0 2px 4px 0 rgba(0,0,0,0.05)`
  - `--border-in-light: 1px solid rgb(222, 222, 222)`
  - `--border-in-dark: 1px solid rgb(136, 136, 136)`

Dark theme
- `--white: rgb(30, 30, 30)` — surface (dark)
- `--black: rgb(187, 187, 187)` — primary text (light)
- `--gray: rgb(21, 21, 21)` — page background (dark)
- `--light-gray: rgb(120, 120, 120)` — secondary text
- `--primary: rgb(60, 72, 144)` — darker blue accent
- `--second: rgb(36, 40, 52)` — sidebar/secondary bg (dark slate)
- `--hover-color: #323232`
- `--bar-color: rgba(255, 255, 255, 0.1)`
- Borders adapt to semi-transparent whites

Layout variables
- `--window-width/height`, `--sidebar-width`, `--window-content-width`, `--message-max-width`, `--full-height` (responsive overrides applied under 600px)

## Typography

- Global family (in `globals.scss`): Noto Sans as primary, with system fallbacks
- Font files: WOFF2 under `public/fonts/notosans` and CSS at `public/fonts/font.css`
- Sizes: 12–20px commonly used in components; headings are bold, compact; body text dark-on-light

## Core Components and Styles

- Container/window (`home.module.scss`):
  - White rounded card with subtle border and deep ambient shadow (`--shadow`)
  - Sidebar (`--second` background), content pane with header (`window.scss`)
- Sidebar (history and settings):
  - Chat item cards: white, soft shadow, hover bg, selected border in `--primary`
  - Drag handle for resizing
- Chat area (`chat.module.scss` + `chat.tsx`):
  - Message bubbles constrained by `--message-max-width` (80% desktop, 100% mobile)
  - Quick action chips, context prompts, prompt toast (pill with shadow)
  - Attach image tiles with hover template overlay
- Buttons (`button.module.scss`):
  - `.icon-button` base with variants `.primary`, `.danger`; primary uses `--primary` with white text
- UI library (`ui-lib.module.scss`):
  - Cards, popovers, tooltips, list items, modal (sheet from bottom), toasts
  - Inputs: white bg, rounded, `--border-in-light`
- Animations: `slide-in`, `slide-in-from-top`, shared across components

## Visual Character

- Neutral, calm palette dominated by whites, soft grays, and a muted blue accent
- High-contrast but soft: thin borders, pill buttons, gentle shadows
- Light mode default; dark mode balanced and legible
- Dense yet airy layout: compact text sizes, ample paddings, clear separation

## Gaps vs Our Current Frontend

- Our app uses Tailwind classes and a brighter blue/amber/indigo theme, plus pastel page gradients and a gradient header bar. The web-llm theme is more neutral/minimal, with no gradient header and a two-pane windowed layout.
- Robust code relies on SCSS variables; our app uses Tailwind tokens + some CSS variables. Class names don’t match, so a direct drop-in is not feasible.
- Fonts: We use Inter via Google; web-llm ships Noto Sans locally.

## Adaptation Strategy (Options)

Option A — Tailwind-aligned reskin (recommended)
- Map web-llm tokens to Tailwind theme `extend.colors` and re-style our components using Tailwind classes that approximate the SCSS look.
- Keep our existing DOM structure; update styles for cards, buttons, inputs, bubbles.
- Benefits: no React/Next dependency; consistent with our current stack; reduces CSS bloat.

Option B — Hybrid CSS variables
- Import the web-llm CSS variable set into a new stylesheet (e.g., `static/css/webllm-theme.css`).
- Update our CSS/HTML to consume `var(--primary)`, `--white`, `--second`, etc., for colors/borders/shadows.
- Benefits: closer visual parity; easier to maintain across themes; still no React.

Option C — Full UI transplant
- Port selected SCSS modules into plain CSS and replicate DOM structure. Not recommended due to complexity and React-specific interactions.

## Concrete Mapping (A or B)

- Primary accent: `--primary` → Tailwind `primary` (muted blue ~ #5A6087)
- Surfaces: `--white` (#fff), `--second` (#E4E5F1 light bg), gray page bg (#F0F0F0)
- Text: `--black` (#303030), `--light-gray` (#787878)
- Borders: use 1px subtle (`#DEDEDE` light)
- Shadows: main card ambient vs component soft shadow
- Message bubbles: white for bot; pale primary tint for user bubbles
- Buttons: `.icon-button.primary` → solid primary; default → white with border

## Integration Steps (proposed)

1) Add `static/css/webllm-theme.css` defining the variable tokens for light/dark.
2) Switch our global font to Noto Sans (optional) by copying `public/fonts` and including `public/fonts/font.css` in the template; or keep Inter but tune sizes/weights.
3) Update `templates/index.html` classes to approximate:
   - Replace gradient header with a white header + thin bottom border; or keep branding but use neutral content container.
   - Ensure main card uses white bg, subtle border, ambient shadow.
   - Update chat bubbles and buttons to match muted blue accent.
4) Remove unused legacy CSS from `static/css/style.css` as we converge.

If you want, I can implement Option B now (add variables + minimal overrides) and then iterate on the Tailwind mappings to visually align with web-llm while preserving our current layout and brand.

