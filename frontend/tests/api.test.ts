import { describe, expect, it } from 'vitest';

import { errMsg } from '../lib/api';

describe('errMsg', () => {
  it('returns a plain string payload unchanged', () => {
    expect(errMsg({ response: { data: 'boom' } })).toBe('boom');
  });

  it('extracts FastAPI string details', () => {
    expect(errMsg({ response: { data: { detail: 'Not found' } } })).toBe('Not found');
  });

  it('joins FastAPI validation error arrays', () => {
    const err = {
      response: { data: { detail: [{ msg: 'field required' }, { msg: 'bad value' }] } },
    };
    expect(errMsg(err)).toBe('field required; bad value');
  });

  it('falls back gracefully without a response', () => {
    expect(errMsg(new Error('network down'), 'fallback')).toBe('network down');
    expect(errMsg(null, 'fallback')).toBe('fallback');
  });
});
