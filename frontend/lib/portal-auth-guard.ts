/**
 * Placeholder auth guard for the (portal) route group. Always allows access
 * for now — there is no session/token concept yet in STORY-007's scope.
 * STORY-024 replaces this with a real check against `features/auth/`'s
 * session/auth-context provider.
 *
 * Lives outside `app/(portal)/layout.tsx` because Next.js 15 restricts
 * special files (`layout.tsx`/`page.tsx`) to a fixed set of exports
 * (`default`, `metadata`, `generateMetadata`, ...) — a custom named export
 * there fails `tsc` against the generated `.next/types` route typings.
 */
export function isAuthenticatedPlaceholder(): boolean {
  return true;
}
