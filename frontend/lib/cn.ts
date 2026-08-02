/**
 * Minimal className combinator (no external dependency needed for STORY-007's
 * scope). Falsy values are dropped; truthy values are joined with a space.
 */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
