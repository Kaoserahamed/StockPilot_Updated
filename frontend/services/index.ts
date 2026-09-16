/**
 * Barrel export for the client's only fetch layer.
 *
 * Pages and hooks import from `@/services` (or a specific module) so that a
 * backend contract change is a one-file edit here rather than a hunt through
 * components. See `docs/ARCHITECTURE.md`.
 */

export * as admin from './admin';
export * as ai from './ai';
export * as analytics from './analytics';
export * as auth from './auth';
export * as catalogue from './catalogue';
export * as finance from './finance';
export * as inventory from './inventory';
export * as parties from './parties';
export * as reports from './reports';
export * as system from './system';
export * as trading from './trading';

export type * from '@/types';
