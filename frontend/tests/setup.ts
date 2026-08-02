import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// vitest.config.ts does not set `test.globals: true`, so React Testing
// Library's automatic afterEach-cleanup detection never fires (it looks for
// a global `afterEach`). Register it explicitly so DOM state from one test
// doesn't leak into the next.
afterEach(() => {
  cleanup();
});
