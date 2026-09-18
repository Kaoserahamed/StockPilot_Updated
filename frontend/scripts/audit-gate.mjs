#!/usr/bin/env node
/**
 * Dependency audit gate used by CI.
 *
 * Runs `npm audit --json` and fails the build when a HIGH or CRITICAL advisory
 * affects a package that is not on the documented deferral list below.
 *
 * Why a deferral list rather than plain `npm audit --audit-level=high`?
 *   After the vitest/vite stack was upgraded (which cleared three advisories),
 *   exactly two packages still carry a high/critical finding and neither can be
 *   fixed without a breaking framework upgrade (Next.js 14 -> 16, which also
 *   means React 19 and the ESLint flat config). A permanently red pipeline hides
 *   *new* findings, so those two are recorded here with the mitigation already in
 *   place and the follow-up that removes them. Accepted findings are still
 *   printed on every run, so they stay visible in CI logs and in review.
 *
 * The list is deliberately strict: it records the exact advisory IDs known when
 * it was written. A new package with a high/critical finding, a *new* advisory
 * against a deferred package, or a severity escalation all fail the build.
 *
 * Usage:
 *   npm run audit              # from the frontend directory
 *
 * Exit codes: 0 = no unallowlisted findings, 1 = findings to act on.
 */
import { execFileSync } from 'node:child_process';

/**
 * package -> { severity, advisories, reason, mitigation, followUp }
 * Remove an entry as soon as the upgrade that resolves it lands.
 */
const DEFERRED_UPGRADES = new Map([
  [
    'next',
    {
      severity: 'critical',
      advisories: [
        'GHSA-2xp9-vwfh-vxw4',
        'GHSA-36qx-fr4f-26g5',
        'GHSA-3g8h-86w9-wvmq',
        'GHSA-3x4c-7xq6-9pq8',
        'GHSA-4633-3j49-mh5q',
        'GHSA-4c39-4ccg-62r3',
        'GHSA-68g3-v927-f742',
        'GHSA-89xv-2m56-2m9x',
        'GHSA-8h8q-6873-q5fj',
        'GHSA-955p-x3mx-jcvp',
        'GHSA-9g9p-9gw9-jx7f',
        'GHSA-c4j6-fc7j-m34r',
        'GHSA-ffhc-5mcf-pf4q',
        'GHSA-ggv3-7p47-pfv8',
        'GHSA-gx5p-jg67-6x7h',
        'GHSA-h25m-26qc-wcjf',
        'GHSA-h64f-5h5j-jqjh',
        'GHSA-m99w-x7hq-7vfj',
        'GHSA-p293-qw3h-jr36',
        'GHSA-p9j2-gv94-2wf4',
        'GHSA-q4gf-8mx6-v5v3',
        'GHSA-vfv6-92ff-j949',
        'GHSA-wfc6-r584-vfw7',
      ],
      reason:
        'Twenty-three advisories against Next.js 14, including an unauthenticated RCE in the Image Optimization API plus SSRF and cache-poisoning issues.',
      mitigation:
        'next/image is unused and the `images` block (AVIF output + wildcard remotePatterns) was removed from next.config.mjs; the API is a separate origin and no untrusted remote images are fetched.',
      followUp: 'Upgrade to Next.js 16 (breaking: React 19, ESLint flat config). See SECURITY.md.',
    },
  ],
  [
    'postcss',
    {
      severity: 'high',
      advisories: [
        'GHSA-6g55-p6wh-862q',
        'GHSA-fxqj-rqcc-2cmp',
        'GHSA-qx2v-qp2m-jg93',
        'GHSA-r28c-9q8g-f849',
      ],
      reason:
        'Four postcss advisories: XSS via unescaped </style> in stringify output, and arbitrary file read / path traversal via sourceMappingURL.',
      mitigation:
        'Build-time only, and reached solely through the postcss copy bundled inside Next.js; no untrusted CSS is compiled.',
      followUp: 'Resolved by the Next.js 16 upgrade.',
    },
  ],
]);

/**
 * Uppercased advisory-id sets, built once from the table above.
 *
 * `collectAdvisoryIds` upper-cases what GitHub reports. GHSA ids are canonically
 * uppercase, so the comparison happens in that case - the recorded list above
 * stays in the lower-case form GitHub prints in advisory URLs because it is
 * easier to read and to diff. (The previous revision of this file mixed the two
 * cases, so no entry could ever match.)
 */
const DEFERRED_ADVISORY_IDS = new Map(
  [...DEFERRED_UPGRADES].map(([name, entry]) => [
    name,
    new Set(entry.advisories.map((id) => id.toUpperCase())),
  ])
);
const GHSA_PATTERN = /GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}/i;
// `npm` is a shell script on POSIX but an `npm.cmd` shim on Windows, and Node
// refuses to spawn a .cmd directly (EINVAL - the CVE-2024-27980 hardening), so
// Windows goes through the shell. The argument list below is fixed, so there is
// nothing for the shell to interpret. This keeps the gate working on a Windows
// checkout (documented in CONTRIBUTING.md) and on the Linux CI runner alike.
const IS_WINDOWS = process.platform === 'win32';
const NPM = IS_WINDOWS ? 'npm.cmd' : 'npm';
const SEVERITY_RANK = { moderate: 1, high: 2, critical: 3 };

function runAuditJson() {
  try {
    return execFileSync(NPM, ['audit', '--json'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      shell: IS_WINDOWS,
    });
  } catch (error) {
    // npm exits non-zero when findings exist; the JSON report is still on stdout.
    if (error.stdout) return error.stdout;
    throw error;
  }
}

function collectAdvisoryIds(vulnerability) {
  const ids = new Set();
  for (const via of vulnerability.via ?? []) {
    if (typeof via !== 'object' || !via.url) continue;
    const match = GHSA_PATTERN.exec(via.url);
    if (match) ids.add(match[0].toUpperCase());
  }
  return [...ids];
}

function main() {
  const report = JSON.parse(runAuditJson());
  const vulnerabilities = Object.entries(report.vulnerabilities ?? {});

  const blocking = [];
  const accepted = [];

  for (const [name, vulnerability] of vulnerabilities) {
    const severity = vulnerability.severity;
    if (severity !== 'high' && severity !== 'critical') continue;

    const entry = DEFERRED_UPGRADES.get(name);
    const ids = collectAdvisoryIds(vulnerability);
    // A deferred package is tolerated only for the exact advisory set recorded
    // above, and only at the severity it was recorded at: a new advisory, a new
    // package or a severity escalation is a finding to act on.
    const unknown = entry ? ids.filter((id) => !DEFERRED_ADVISORY_IDS.get(name).has(id)) : ids;
    const escalated = entry ? SEVERITY_RANK[severity] > SEVERITY_RANK[entry.severity] : false;

    if (entry && ids.length > 0 && unknown.length === 0 && !escalated) {
      accepted.push({ name, severity, ids });
    } else {
      blocking.push({
        name,
        severity,
        ids: unknown.length ? unknown : ids,
        fixAvailable: vulnerability.fixAvailable,
      });
    }
  }

  if (accepted.length > 0) {
    console.log('\nAccepted advisories (documented deferrals, still visible for review):');
    for (const item of accepted) {
      const entry = DEFERRED_UPGRADES.get(item.name);
      console.log(
        `  - ${item.name} (${item.severity}) ${item.ids.length} recorded advisory/advisories`
      );
      console.log(`      reason     : ${entry.reason}`);
      console.log(`      mitigation : ${entry.mitigation}`);
      console.log(`      follow-up  : ${entry.followUp}`);
    }
  }

  if (blocking.length > 0) {
    console.error('\nDependency audit FAILED - unallowlisted high/critical advisories:\n');
    for (const item of blocking) {
      console.error(
        `  - ${item.name} (${item.severity}) ${item.ids.join(', ') || 'unknown advisory'}`
      );
      console.error(`      fix available: ${JSON.stringify(item.fixAvailable)}`);
    }
    console.error(
      '\nFix the finding, or add a reviewed entry to DEFERRED_UPGRADES in scripts/audit-gate.mjs.\n'
    );
    return 1;
  }

  console.log('\nDependency audit passed: no unallowlisted high/critical advisories.\n');
  return 0;
}

process.exit(main());
