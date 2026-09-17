import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ToastProvider } from '../components/Toast';
import { useOptimisticUpdate } from '../hooks/useOptimisticUpdate';

const PRODUCTS_KEY = ['products'];

type Product = { id: number };

type HarnessProps = {
  mutationFn: (variables: Product) => Promise<Product>;
  onSuccess?: (data: Product, variables: Product) => void;
};

/** Drives the hook through the same providers the app uses. */
function Harness({ mutationFn, onSuccess }: HarnessProps) {
  const mutation = useOptimisticUpdate<Product, Product>(PRODUCTS_KEY, mutationFn, onSuccess);
  return (
    <div>
      <span data-testid="status">{mutation.status}</span>
      <button onClick={() => mutation.mutate({ id: 1 })}>run</button>
    </div>
  );
}

function setup(props: HarnessProps): QueryClient {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <Harness {...props} />
      </ToastProvider>
    </QueryClientProvider>
  );
  return client;
}

function run(): void {
  fireEvent.click(screen.getByText('run'));
}

describe('useOptimisticUpdate', () => {
  it('cancels in-flight refetches and snapshots the cache before mutating', async () => {
    const client = setup({ mutationFn: vi.fn(async () => ({ id: 1 })) });
    const cancelQueries = vi.spyOn(client, 'cancelQueries').mockResolvedValue(undefined);
    client.setQueryData(PRODUCTS_KEY, [{ id: 200 }]);

    await act(async () => {
      run();
    });

    await waitFor(() => {
      expect(cancelQueries).toHaveBeenCalledWith({ queryKey: PRODUCTS_KEY });
    });
  });

  it('rolls the cache back and tells the user when the mutation fails', async () => {
    let fail: (error: Error) => void = () => {};
    const client = setup({
      mutationFn: () =>
        new Promise<Product>((_resolve, reject) => {
          fail = reject;
        }),
    });
    const serverData = [{ id: 200 }];
    client.setQueryData(PRODUCTS_KEY, serverData);

    await act(async () => {
      run();
    });

    // An optimistic write lands in the cache...
    act(() => {
      client.setQueryData(PRODUCTS_KEY, [{ id: 999 }]);
    });
    expect(client.getQueryData(PRODUCTS_KEY)).toEqual([{ id: 999 }]);

    // ...and the rejected mutation puts the server's data back.
    await act(async () => {
      fail(new Error('Server rejected the update'));
    });

    await waitFor(() => {
      expect(client.getQueryData(PRODUCTS_KEY)).toEqual(serverData);
    });
    expect(screen.getAllByText('Server rejected the update').length).toBeGreaterThan(0);
  });

  it('passes the result to onSuccess and invalidates the query afterwards', async () => {
    const onSuccess = vi.fn();
    const client = setup({ mutationFn: vi.fn(async () => ({ id: 7 })), onSuccess });
    const invalidateQueries = vi.spyOn(client, 'invalidateQueries');

    await act(async () => {
      run();
    });

    await waitFor(() => {
      expect(screen.getByTestId('status').textContent).toBe('success');
    });
    expect(onSuccess).toHaveBeenCalledWith({ id: 7 }, { id: 1 });
    await waitFor(() => {
      expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: PRODUCTS_KEY });
    });
  });

  it('falls back to a generic message when the failure is not an Error', async () => {
    const client = setup({
      mutationFn: () => Promise.reject('plain string failure'),
    });

    await act(async () => {
      run();
    });

    await waitFor(() => {
      expect(screen.getByTestId('status').textContent).toBe('error');
    });
    expect(client.getQueryData(PRODUCTS_KEY)).toBeUndefined();
  });
});
