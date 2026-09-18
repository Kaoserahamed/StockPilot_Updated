import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';

function keyEvent(key: string, init: KeyboardEventInit = {}): KeyboardEvent {
  return new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
}

describe('useKeyboardShortcuts', () => {
  it('fires the matching shortcut on keydown', () => {
    const checkout = vi.fn();
    const { unmount } = renderHook(() => useKeyboardShortcuts({ f2: checkout }));
    act(() => {
      window.dispatchEvent(keyEvent('F2'));
    });
    expect(checkout.mock.calls.length).toBe(1);
    unmount();
  });

  it('stays disabled when enabled=false', () => {
    const save = vi.fn();
    const { unmount } = renderHook(() => useKeyboardShortcuts({ 'ctrl+s': save }, false));
    act(() => {
      window.dispatchEvent(keyEvent('s', { ctrlKey: true }));
    });
    expect(save.mock.calls.length).toBe(0);
    unmount();
  });

  it('composes modifier keys into the documented combination syntax', () => {
    const reorder = vi.fn();
    const alt = vi.fn();
    const { unmount } = renderHook(() =>
      useKeyboardShortcuts({ 'ctrl+shift+p': reorder, 'alt+r': alt })
    );

    act(() => {
      window.dispatchEvent(keyEvent('P', { ctrlKey: true, shiftKey: true }));
    });
    act(() => {
      window.dispatchEvent(keyEvent('r', { altKey: true }));
    });

    expect(reorder.mock.calls.length).toBe(1);
    expect(alt.mock.calls.length).toBe(1);
    unmount();
  });

  it('ignores shortcuts typed into form controls, except escape', () => {
    const checkout = vi.fn();
    const close = vi.fn();
    const { unmount } = renderHook(() =>
      useKeyboardShortcuts({ 'ctrl+s': checkout, escape: close })
    );

    const input = document.createElement('input');
    document.body.appendChild(input);

    act(() => {
      input.dispatchEvent(keyEvent('s', { ctrlKey: true, bubbles: true }));
    });
    expect(checkout.mock.calls.length).toBe(0);

    act(() => {
      input.dispatchEvent(keyEvent('Escape', { bubbles: true }));
    });
    expect(close.mock.calls.length).toBe(1);

    // A key that is not mapped inside a field stays inert.
    act(() => {
      input.dispatchEvent(keyEvent('f2', { bubbles: true }));
    });
    expect(checkout.mock.calls.length).toBe(0);

    input.remove();
    unmount();
  });
});
