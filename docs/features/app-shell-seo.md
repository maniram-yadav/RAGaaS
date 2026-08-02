# App shell + SEO scaffolding

<!-- Filled in by the feature-doc-writer skill when the owning agent completes a story. See
     .claude/rules/documentation-standards.md for the rules behind each section. -->

## Overview

Implements the Next.js 15 App Router shell described in plan §9: the three route groups —
`(marketing)` (SEO-facing, SSR'd pages), `(auth)` (login/signup shells), and `(portal)` (the
authenticated app, behind a guard) — plus the SEO primitives (`generateMetadata` per page,
`sitemap.xml`/`robots.txt` metadata routes) and the shared design system (Tailwind design tokens +
`components/ui` primitives) that every later frontend story builds on. This story only owns
structure/shell/styling; no route calls a real backend endpoint yet (auth wiring is STORY-024, chat is
STORY-025, billing is STORY-058).

## Interfaces / contracts

- Route group pages (Server Components, no `"use client"` unless noted):
  - `app/(marketing)/layout.tsx`, `app/(marketing)/page.tsx` (home), `app/(marketing)/pricing/page.tsx`,
    `app/(marketing)/about/page.tsx` — each page exports `generateMetadata(): Metadata`.
  - `app/(auth)/layout.tsx`, `app/(auth)/login/page.tsx`, `app/(auth)/signup/page.tsx` — static form
    shells (`noindex` via `generateMetadata`'s `robots` field); submit buttons are `disabled` pending
    STORY-024's real handlers.
  - `app/(portal)/layout.tsx` and `app/(portal)/dashboard/page.tsx`. The layout calls
    `isAuthenticatedPlaceholder(): boolean` (in `lib/portal-auth-guard.ts` — Next.js 15 rejects custom
    named exports from `layout.tsx`/`page.tsx` files against the generated route types, so the guard
    lives in its own module), currently a stub that always returns `true`; the layout wraps children in
    a `redirect("/login")` guard for when it doesn't — replaced by a real session/auth-context check in
    STORY-024.
- SEO metadata routes (Next.js file conventions, resolve to `/sitemap.xml` and `/robots.txt`):
  - `app/sitemap.ts` — default export `sitemap(): MetadataRoute.Sitemap`, lists the three public
    `(marketing)` URLs.
  - `app/robots.ts` — default export `robots(): MetadataRoute.Robots`, allows `/`, disallows
    `/dashboard` and `/api/`, points `sitemap` at `/sitemap.xml`.
- Design system (`components/ui/`):
  - `Button` (`variant`: primary/secondary/danger/ghost, `size`: sm/md/lg)
  - `Card` (optional `title` + children)
  - `Modal` (`"use client"`; `open`/`onClose`/`title`; closes on Escape or backdrop click)
  - `Table<Row>` (`columns`, `rows`, `emptyState` — renders an empty-state row when `rows` is empty)
  - Barrel export: `components/ui/index.ts`
  - `lib/cn.ts` — minimal className combinator used by the primitives above.
- `tailwind.config.ts` — design tokens: `brand`/`neutral` color scales, `success`/`warning`/`danger`/
  `background`/`foreground` semantic colors, `spacing` (`18`, `22`), `fontFamily` (`sans`/`mono`, backed
  by CSS variables in `styles/globals.css`), `fontSize` scale, `borderRadius.card`.

## Config knobs

- `NEXT_PUBLIC_SITE_URL` (new, added via `add-config-key` for this story) — canonical frontend origin
  used by `app/sitemap.ts`/`app/robots.ts` to build absolute URLs; defaults to `http://localhost:3000`
  in code if unset.
- `NEXT_PUBLIC_API_BASE_URL` (existing, unused by this story — no route here calls the backend yet).

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule and
both keys' entries.

## Testing

- Location: `frontend/tests/app/{marketing,auth,portal,seo}.test.tsx|ts`,
  `frontend/tests/components/ui/{Button,Card,Modal,Table}.test.tsx`, and the STORY-001 smoke test
  `frontend/tests/route-groups.test.tsx` (updated to match this story's page content).
- Run with: `cd frontend && npm test` (Vitest + React Testing Library, jsdom environment).
- Covers: every route group page renders without throwing; `generateMetadata` returns a title/
  description (and `robots: { index: false }` for the `(auth)` pages); the `(portal)` placeholder guard's
  current always-allow behavior and that the layout renders its children; `sitemap()`/`robots()` return
  well-formed absolute URLs and the expected allow/disallow rules; each `components/ui` primitive's
  rendering, variant/size classes, empty-state behavior (`Table`), and interaction behavior (`Button`
  click, `Modal` open/close via backdrop click/Escape key).
- Also fixed a latent test-infra gap while writing these tests: `frontend/tests/setup.ts` now calls
  `@testing-library/react`'s `cleanup()` in an explicit `afterEach` (Vitest's `test.globals` is `false`
  in `vitest.config.ts`, so RTL's automatic cleanup detection never registered, which had been letting
  DOM state leak between tests in the same file).
- Manually verified: `npm run dev`, then `curl` against `/`, `/pricing`, `/about`, `/login`, `/signup`,
  `/dashboard`, `/sitemap.xml`, and `/robots.txt` all returned `200`; inspected the rendered home page
  HTML for `<title>`, `meta[name=description]`, and `og:*`/`twitter:*` tags (SEO sanity check per this
  story's acceptance criteria — the formal Lighthouse CI gate is STORY-065).

## Story references

- STORY-007 — Next.js app shell + SEO scaffolding: three route groups, `generateMetadata`,
  `sitemap.xml`/`robots.txt`, Tailwind design tokens, `components/ui` primitives (Button/Card/Modal/
  Table).
