# Yarn Chat Frontend — Look & Feel, Colors, and Styling

This document captures the current visual system used by the app’s frontend (`templates/index.html` and assets under `static/`). It’s meant to guide refinements and any future UI rewrites or migrations.

## Overview

- Frameworks: Tailwind CSS via CDN (with a small runtime config) + a custom CSS file (`static/css/style.css`).
- Icons: Bootstrap Icons (CDN) for header/actions.
- Fonts: Inter (Google Fonts) is applied globally; a legacy system stack is defined in `style.css` but overridden by inline styles in `index.html`.
- Layout: A soft, welcoming chat card over a pastel gradient page background. Large radii, light borders, and gentle shadows convey a friendly, approachable feel suitable for youth mental health support.

## Color Palette

There are two overlapping color systems in use:

1) Tailwind palette (default + minimal extension)
- Primary: `#2563eb` (Tailwind blue-600) — configured in `static/js/tailwind-config.js` as `primary`.
- Accent: `#f59e0b` (Tailwind amber-500) — configured as `accent`.
- Header gradient: `from-indigo-500` to `to-purple-500` (Tailwind defaults).
- Background gradient (page): `from-amber-50 via-rose-50 to-orange-50` (very soft pastels).
- Brand roundel (avatar chip): `from-yellow-400 to-green-400`.
- Neutrals: `text-neutral-900`, `text-neutral-600/700`, borders with `neutral-200/300`.
- CTAs and helpers: `amber-50/200/600/700`, `blue-50/200/600/700` for help cards and action buttons.

2) Custom CSS variables (`static/css/style.css`)
- `--primary-color: #7c4dff` (vibrant purple)
- `--secondary-color: #ff6b6b` (coral red)
- `--accent-color: #4ecdc4` (turquoise)
- `--warm-orange: #ff9a56`
- `--earth-brown: #8b6f47`
- `--sky-blue: #87ceeb`
- `--sage-green: #95b88f`
- `--chat-bg: linear-gradient(135deg, #667eea → #764ba2)` (indigo → purple)
- `--message-user: #f0f4f8`, `--message-bot: #ffffff`
- Text: `--text-primary: #2d3748` (slate-800-ish), `--text-secondary: #718096` (slate-500-ish)

Notes
- The active UI (Tailwind classes) primarily uses the Tailwind palette (blue/amber/indigo/purple + neutrals) and the pastel gradient background.
- The custom CSS variables define an alternate/chat-specific look (gradient message bubbles, dark debug panel) that is only partially used by the current markup.

## Typography

- Primary font: Inter, weights 400/500/600/700.
- Effective global font-family is set via an inline style in `index.html`, which overrides the system stack in `style.css`.
- Scale: Headlines use Tailwind (`text-2xl`/`text-3xl`), body copy with neutral grays (`text-neutral-600/700/900`).

## Layout & Components

- Page background: Pastel diagonal gradient (`amber-50 → rose-50 → orange-50`).
- Main container: White, rounded (`rounded-3xl`), subtle ring (`ring-1 ring-neutral-200`), and `shadow-2xl`.
- Header bar: Full-width gradient (`indigo-500 → purple-500`), white text, pill buttons with translucent white hovers, environment status chip (`#envChip`).
- Branding: Circular avatar with yellow→green gradient and a bold initial.
- Chat area: Generous spacing, left-aligned bot messages with white bubbles; user messages right-aligned with a pale primary background (`bg-primary/10`).
- History drawer: Right-side slide-over, neutral border, list of session items in a clean, compact style.
- Help panel: Information cards with amber/blue accents; clear CTAs (“Call”, “Visit site”).
- Favicon: Blue circle (`#2563eb`) with a white “Y”.

## Shadows, Radii, and Motion

- Radii: Large throughout (e.g., `rounded-3xl` for main card, `rounded-full` for chips, `rounded-xl` for bubbles).
- Shadows: Tailwind `shadow-2xl` on the main card; `style.css` defines soft/medium shadow variables used by the legacy chat layout.
- Motion: `style.css` defines `slideUp`, `fadeIn`, `slideIn`, `pulse` animations; the current Tailwind-based markup uses minimal animation directly, though some debug update highlights are present in JS.

## Iconography

- Bootstrap Icons provide simple, crisp controls (history, help, close, etc.).
- Sizes and weights are consistent, leaning toward a modern, minimal look.

## Accessibility & States

- Contrast: White-on-gradient header and dark-on-light content maintain good readability.
- Focus: `style.css` includes `*:focus-visible` outlines in the primary color.
- Disclaimers: Prominent info panel near the start to set expectations and provide safety guidance.

## Notable Inconsistencies / Cleanup Targets

- Mixed color systems: Tailwind palette + custom CSS variables both define “primary”/“accent” ideas with different hues. Unify on one system (recommended: Tailwind, with an extended theme) for consistency.
- Encoding artifacts: The title and some header glyphs show replacement characters (�). Normalize templates to UTF‑8 and fix visible text (e.g., stray `dY`/`<`).
- Tailwind in production: The console warns against using `cdn.tailwindcss.com` in production. Precompile Tailwind (CLI/PostCSS) and serve a static CSS bundle.
- Debug panel styles: `style.css` includes a dark “debug panel,” but the corresponding markup isn’t present in `index.html`; either add the panel or remove unused CSS.
- Fonts: `style.css` sets a system stack that is overridden by inline Inter. Keep a single source of truth (prefer Inter via one CSS import + class or global rule).
- Component parity: `style.css` includes quick actions, typing indicators, and session summary styles not fully wired to the Tailwind-driven markup. Decide which set to keep and remove dead styles.

## Suggested Direction

- Consolidate on Tailwind: Move color tokens into Tailwind theme `extend.colors` (primary, accent, neutrals if customized) and refactor components to use these classes.
- Precompile CSS: Replace CDN Tailwind with a built bundle for production; keep the runtime config only for dev.
- Normalize typography: Define fonts and sizes in Tailwind config and remove conflicting base styles.
- Clean assets: Remove unused CSS sections or reintroduce the intended components (debug panel, quick actions) in the markup.
- Fix artifacts: Clean up UTF‑8 issues and any placeholder text.

---

This summary reflects the current state of the checked-in frontend. After you share the new “robust” codebase, I’ll extract its frontend, compare component-by-component (colors, spacing, states, behaviors), and adapt it to match the above system or propose a unified, updated design.

