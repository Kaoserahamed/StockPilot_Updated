import { describe, expect, it } from 'vitest';

import { escapeHtml, isValidEmail, isValidPhone, sanitizeInput } from '../lib/sanitize';

describe('sanitize helpers', () => {
  it('escapes HTML special characters', () => {
    expect(escapeHtml('<b>&"\'</b>')).toBe('&lt;b&gt;&amp;&quot;&#x27;&lt;/b&gt;');
  });

  it('trims and truncates input', () => {
    expect(sanitizeInput('  hello  ')).toBe('hello');
    expect(sanitizeInput('abcdef', 3)).toBe('abc');
  });

  it('validates email addresses', () => {
    expect(isValidEmail('owner@shop.com')).toBe(true);
    expect(isValidEmail('not-an-email')).toBe(false);
  });

  it('validates phone numbers', () => {
    expect(isValidPhone('01700000000')).toBe(true);
    expect(isValidPhone('+8801700000000')).toBe(true);
    expect(isValidPhone('abc')).toBe(false);
  });
});
