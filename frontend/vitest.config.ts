import path from 'node:path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: { '@': path.resolve(__dirname, '.') },
  },
  // Next.js compiles JSX with the automatic runtime, so components do not need
  // to import React. Vitest defaults to the classic runtime, which would fail on
  // every such file (e.g. lib/store.tsx) - align the two.
  esbuild: {
    jsx: 'automatic',
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    globals: true,
    include: ['tests/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'json-summary'],
      // The route pages under app/ are verified by the render smoke tests in
      // tests/pages.test.ts and by `npm run build`; measuring them here would
      // drown the signal. The floors below cover the unit-tested modules and
      // `all: true` keeps a newly added, untested module visible at 0%.
      all: true,
      include: [
        'components/**/*.{ts,tsx}',
        'hooks/**/*.{ts,tsx}',
        'lib/**/*.{ts,tsx}',
        'services/**/*.ts',
      ],
      thresholds: {
        // Deliberately close to today's measured coverage (lines ~47.6%,
        // functions ~42.5%, branches ~76.4% over these four directories). With
        // `all: true`, adding an untested module lowers the number and fails
        // the build - that is the point: new code arrives with its tests.
        lines: 45,
        functions: 40,
        branches: 70,
        statements: 45,
      },
    },
  },
});
