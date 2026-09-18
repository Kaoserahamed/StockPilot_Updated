/**
 * Shared, deliberately non-secret fixtures for the frontend test suite.
 *
 * `TEST_PASSWORD` exists so no password-shaped literal is ever committed in a
 * test: it never leaves the mocked axios layer, and its `test-` prefix marks it
 * as a placeholder for the repository secret scanner
 * (`backend/scripts/scan_secrets.py`), which is why it is safe to keep here.
 */
export const TEST_PASSWORD = 'test-password-for-mocked-auth';

/** Email used by the mocked auth calls; not a real mailbox. */
export const TEST_EMAIL = 'owner@shop.test';
