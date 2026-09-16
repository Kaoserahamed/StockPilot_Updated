#!/usr/bin/env node
/**
 * Dependency audit gate used by CI.
 *
 * Runs `npm audit --json` and fails the build when any HIGH or CRITICAL advisory
 * is present that is not on the documented allowlist below.
 *
 * Why an allowlist instead of plain `npm audit --audit-level=high`?
 *   Two advisories currently have no fix that can be applied without a breaking
 *   framework upgrade. A permanently red pipeline hides *new* findings, so those
 *   two are recorded here with the mitigation that is already in place and the
 *   follow-up that removes them. Allowlisted items are still printed on every
 *   run, so they stay visible in CI logs and in review.
 *
 * Usage:
 *   npm run audit              # from the frontend directory
 *
 * Exit codes: 0 = no unallowlisted findings, 1 = findings to act on.
 */
import { execFileSync } from 'node:child_process';

/**
 * advisory id -> { reason, mitigation, followUp }
 * Remove an entry as soon as the upgrade that resolves it lands.
 */
const ALLOWLIST = new Map([
  [
    'GHSA-2xp9-vwfh-vxw4',
    {
      package: 'next',
      severity: 'critical',
      reason: 'Unauthenticated RCE in the Image Optimization API when AVIF output is used.',
      mitigation:
        'next/image is unused and the `images` block (AVIF output + wildcard remotePatterns) was removed from next.config.mjs, so the vulnerable endpoint is never exercised.',
      followUp:
        'Upgrade to Next.js 16 (breaking: React 19, ESLint flat config). See docs/SECURITY.md.',
    },
  ],
  [
    'GHSA-qx2v-qp2m-jg93',
    {
      package: 'postcss',
      severity: 'high',
      reason: 'XSS via unescaped </style> in CSS stringify output.',
      mitigation:
        'Build-time only, and reached solely through the postcss copy bundled inside Next.js; no untrusted CSS is compiled.',
      followUp: 'Resolved by the Next.js 16 upgrade.',
    },
  ],
  [
    'GHSA-6g55-p6wh-862q',
    {
      package: 'postcss',
      severity: 'high',
      reason: 'Arbitrary file read via attacker-controlled sourceMappingURL in CSS comments.',
      mitigation: 'Build-time only; sources are first-party and not attacker-controlled.',
      followUp: 'Resolved by the Next.js 16 upgrade.',
    },
  ],
  [
    'GHSA-fxqj-rqcc-2cmp',
    {
      package: 'postcss',
      severity: 'high',
      reason: 'Incomplete fix of GHSA-6g55-p6wh-862q (reads .map files when `from` is unset).',
      mitigation: 'Build-time only; sources are first-party and not attacker-controlled.',
      followUp: 'Resolved by the Next.js 16 upgrade.',
    },
  ],
  [
    'GHSA-r28c-9q8g-f849',
    {
      package: 'postcss',
      severity: 'high',
      reason: 'Path traversal in previous source-map auto-loading.',
      mitigation: 'Build-time only; sources are first-party and not attacker-controlled.',
      followUp: 'Resolved by the Next.js 16 upgrade.',
    },
  ],
]);

const GHSA_PATTERN = /GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}/i;

function runAuditJson() {
  try {
    return execFileSync('npm', ['audit', '--json'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
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

    const ids = collectAdvisoryIds(vulnerability);
    const unknown = ids.filter((id) => !ALLOWLIST.has(id));

    if (ids.length > 0 && unknown.length === 0) {
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
    console.log('\nAccepted advisories (documented exceptions, still visible for review):');
    for (const item of accepted) {
      for (const id of item.ids) {
        const entry = ALLOWLIST.get(id);
        console.log(`  - ${item.name} (${item.severity}) ${id}`);
        console.log(`      reason     : ${entry.reason}`);
        console.log(`      mitigation : ${entry.mitigation}`);
        console.log(`      follow-up  : ${entry.followUp}`);
      }
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
      '\nFix the finding, or add a reviewed entry to ALLOWLIST in scripts/audit-gate.mjs.\n'
    );
    return 1;
  }

  console.log('\nDependency audit passed: no unallowlisted high/critical advisories.\n');
  return 0;
}

process.exit(main());
