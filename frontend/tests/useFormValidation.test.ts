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
});
