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
});
