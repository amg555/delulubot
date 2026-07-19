---
name: ui-ux-design
description: Apply professional UI/UX design principles when building or modifying any user interface — web pages, apps, dashboards, forms, or components. Use when creating new UI, redesigning existing UI, or when the user asks for something to "look better", "look professional", or "look modern".
---

# UI/UX Design Standards

Apply these principles to every UI task. Don't just make it work — make it look intentional and professional. Avoid generic, templated "AI-default" output (centered hero + 3 feature cards + rounded-corners-everywhere) unless it's genuinely the right fit.

## 1. Establish a design direction before coding

Before writing markup, decide:
- **Mood**: minimal/clean, bold/editorial, playful, technical/dense, luxury, etc.
- **One distinctive element**: an accent color, a typographic choice, an unusual layout grid — something that keeps it from looking like every other generated UI.
- Avoid defaulting to purple gradients, generic sans-serif + rounded cards, and evenly-spaced 3-column grids unless asked for.

## 2. Typography

- Use no more than 2 font families (one for headings, one for body — or a single family with varied weights).
- Establish a clear type scale (e.g. 12/14/16/20/24/32/48px) and stick to it. Don't invent one-off sizes.
- Body text: 16px minimum for readability, line-height 1.5–1.6.
- Headings: line-height 1.1–1.3, tighter letter-spacing on large sizes.
- Limit line length for body copy to ~60–75 characters (`max-width` on text blocks).

## 3. Color

- Build from a small, deliberate palette: 1 primary, 1–2 neutrals (grayscale), 1 accent, plus semantic colors (success/warning/error).
- Neutrals should not be pure gray — lean slightly warm or cool to match the mood.
- Check contrast: body text vs background ≥ 4.5:1, large text/UI components ≥ 3:1 (WCAG AA).
- Use color with purpose (state, hierarchy, brand) — not decoration for its own sake.

## 4. Spacing & layout

- Use a consistent spacing scale (e.g. 4/8/12/16/24/32/48/64px — multiples of 4 or 8). Never eyeball arbitrary padding/margin values.
- Whitespace is a design tool, not empty leftover space — use it to group related elements and separate unrelated ones (proximity principle).
- Align elements to a grid. Nothing should float at an arbitrary position.
- Respect a clear visual hierarchy: size, weight, and color should make it obvious what to look at first, second, third.

## 5. Components

- Buttons: one clear primary action per view/section; secondary actions visually subordinate (outline/ghost style).
- Forms: label above input, inline validation, clear error states with specific messages (not just "invalid input").
- Cards/lists: consistent internal padding, consistent image aspect ratios, don't mix card styles in the same grid.
- Interactive elements need visible hover, focus, active, and disabled states — never rely on cursor change alone.
- Empty states, loading states, and error states are not optional — design them alongside the "happy path."

## 6. Motion

- Use transitions for state changes (hover, open/close, page transition) at 150–300ms with an ease-out curve. Avoid animating things that don't need it.
- Never use motion as the only signal for a state change — pair with color/icon/text for accessibility.

## 7. Accessibility (non-negotiable baseline)

- Every interactive element is keyboard-reachable and has a visible focus state.
- All images have meaningful `alt` text (or `alt=""` if purely decorative).
- Form inputs have associated `<label>` elements.
- Don't convey information by color alone (e.g. pair red/green with icons or text).
- Semantic HTML first (`<button>`, `<nav>`, `<main>`, headings in order) before reaching for `<div>` + ARIA.

## 8. Responsive behavior

- Design mobile-first when feasible; verify layouts at ~375px, ~768px, and ~1440px widths.
- Touch targets ≥ 44x44px on mobile.
- Don't just shrink desktop layouts — reconsider what's essential at each breakpoint.

## 9. Self-review checklist before calling a UI "done"

- [ ] Type scale and spacing scale are consistent throughout (no one-off values)
- [ ] Contrast passes WCAG AA
- [ ] Hover/focus/active/disabled/error/loading/empty states all designed
- [ ] Visual hierarchy guides the eye to the primary action first
- [ ] Nothing looks like an unstyled browser default (unless intentional/minimal style)
- [ ] It doesn't look like a generic template — there's at least one deliberate, distinctive choice

## References

See `references/patterns.md` for common layout patterns (dashboards, forms, landing pages, data tables) if deeper guidance is needed for a specific UI type.
