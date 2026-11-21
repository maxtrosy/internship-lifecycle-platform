# CLAUDE.md

## Frontend Design Standards

These standards apply to DH-05 (Internship and Practicum Management) frontend work in `frontend/`.

- **Read the relevant skills before implementing.** They are installed at project level in `.claude/skills/`:
  - `frontend-design` for visual direction.
  - `ui-ux-pro-max` for UX rules and a local search over guidelines.
  - `bencium-controlled-ux-designer` (folder `controlled-ux-designer`) for design decisions.
  - `web-design-guidelines` for UI and accessibility review.
  - `vercel-react-best-practices` (folder `react-best-practices`) and `vercel-composition-patterns` (folder `composition-patterns`) for React code.
- **The stack overrides the skills.** The frontend is React 18 + TypeScript + Vite, styled with plain CSS: `src/index.css`, plus `src/theme.css` with CSS custom properties and dark mode. It does not use Tailwind, shadcn, Next.js or React 19.
  - Translate any skill example that assumes those tools into the existing CSS variables and components.
  - Skip Next.js/RSC-only rules and React 19-only rules.
- **Keep one coherent design system.** Reuse the existing tokens in `theme.css` and the existing components. Do not introduce parallel palettes, spacing scales or icon sets.
- **Use a corporate-university look: institutional, sober, clean, modern, highly legible.**
  - Avoid purple gradients, glassmorphism, heavy shadows, an excess of cards, decorative animation, saturated colors, emojis and generic "AI-looking" layouts.
  - Prioritize the sidebar, breadcrumbs, tables, forms, and the loading, error, empty and success states.
  - Use consistent SVG icons.
- **Do not invent institutional identity.** Do not create logos, crests, official colors or official typefaces for Horizon University, or present synthetic examples as institutional policy. Ask for official assets instead.
- **Respect what already works.** Keep correct existing components and preserve all functionality, API contracts and endpoints. Do not change the backend or migrations as part of design work.
- **Avoid unnecessary dependencies.** Do not add UI libraries, icon packages, animation libraries or CSS frameworks without explicit approval.
- **Verify responsive behavior and accessibility.** Check at about 390 px (no horizontal scroll) and on desktop. Meet WCAG 2.1 AA: contrast, visible focus, keyboard navigation, labels, `prefers-reduced-motion`.
- **Run the tests after every frontend change.** From `frontend/`, run:
  - `npx vitest run --exclude "e2e/**"`
  - `npx tsc -b`
  - `npx vite build`
  - When flows change, also run the isolated E2E: `python scripts/run_isolated_e2e.py`.
- **Running the `ui-ux-pro-max` search tool.** It is stdlib-only Python and works offline. It is installed as a project skill, so `${CLAUDE_PLUGIN_ROOT}` does not apply. Run it as:
  `python -I .claude/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain <domain>`
  - Do not use `--persist`, `--preview` or `--force` without approval.
  - Do not put private project data in queries.
