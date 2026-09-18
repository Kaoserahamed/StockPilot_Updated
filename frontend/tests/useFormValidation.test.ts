import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useFormValidation } from '../hooks/useFormValidation';

describe('useFormValidation', () => {
  it('flags missing required fields and clears them', () => {
    const { result } = renderHook(() =>
      useFormValidation({ email: { required: true, message: 'Email needed' } })
    );

    let valid = true;
    act(() => {
      valid = result.current.validate({ email: '' });
    });
    expect(valid).toBe(false);
    expect(result.current.errors.email).toBe('Email needed');

    act(() => {
      result.current.clearErrors();
    });
    expect(result.current.errors).toEqual({});
  });

  it('enforces min length, max length and patterns', () => {
    const { result } = renderHook(() =>
      useFormValidation({
        password: { required: true, minLength: 6 },
        code: { maxLength: 4 },
        email: { pattern: /^[^@\s]+@[^@\s]+\.[^@\s]+$/ },
      })
    );

    let valid = true;
    act(() => {
      valid = result.current.validate({
        password: 'abc',
        code: 'toolong',
        email: 'bad',
      });
    });
    expect(valid).toBe(false);
    expect(Object.keys(result.current.errors)).toHaveLength(3);
  });

  it('validates a single field without touching the rest', () => {
    const { result } = renderHook(() =>
      useFormValidation({ name: { required: true }, other: { required: true } })
    );

    act(() => {
      result.current.validateField('name', '');
    });
    expect(result.current.errors.name).toBeTruthy();
    expect(result.current.errors.other).toBeUndefined();
  });

  it('builds default messages when a rule carries no message of its own', () => {
    const { result } = renderHook(() =>
      useFormValidation({
        name: { required: true },
        code: { minLength: 4 },
        tag: { maxLength: 2 },
        email: { pattern: /@/ },
      })
    );

    let valid = true;
    act(() => {
      valid = result.current.validate({ name: '', code: 'ab', tag: 'abc', email: 'nope' });
    });

    expect(valid).toBe(false);
    expect(result.current.errors.name).toBe('name is required');
    expect(result.current.errors.code).toBe('code must be at least 4 characters');
    expect(result.current.errors.tag).toBe('tag must be at most 2 characters');
    expect(result.current.errors.email).toBe('email is invalid');
  });

  it('ignores a field without a rule and clears one error at a time', () => {
    const { result } = renderHook(() =>
      useFormValidation({ name: { required: true }, other: { required: true } })
    );

    act(() => {
      expect(result.current.validateField('unknown', 'anything')).toBe('');
    });

    act(() => {
      result.current.validateField('name', '');
      result.current.validateField('other', '');
    });
    expect(Object.keys(result.current.errors)).toHaveLength(2);

    // A now-valid value removes only its own error.
    act(() => {
      result.current.validateField('name', 'Maya');
    });
    expect(result.current.errors.name).toBeUndefined();
    expect(result.current.errors.other).toBeTruthy();

    act(() => {
      result.current.clearFieldError('other');
    });
    expect(result.current.errors).toEqual({});
  });
});
