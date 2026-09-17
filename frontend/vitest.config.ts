import path from 'node:path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: { '@': path.resolve(__dirname, '.') },
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
        lines: 40,
        functions: 40,
        branches: 60,
        statements: 40,
      },
    },
  },
});
