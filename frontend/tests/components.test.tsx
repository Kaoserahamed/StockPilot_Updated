import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ErrorBoundary } from '../components/ErrorBoundary';
import { Skeleton, SkeletonCard, SkeletonTable } from '../components/Skeleton';
import { Badge, Btn, Card, Empty, SectionTitle, Stat } from '../components/ui';
import { ToastProvider } from '../components/Toast';

describe('shared ui primitives', () => {
  it('renders Card, titles, stats and badges', () => {
    render(
      <div>
        <Card>
          <SectionTitle title="Stock" sub="Levels" />
          <Stat label="Units" value={42} sub="on hand" />
          <Badge tone="green">ok</Badge>
          <Badge tone="red">out</Badge>
          <Empty title="Nothing here" sub="Add stock" />
        </Card>
        <Btn variant="primary">Save</Btn>
        <Btn variant="danger">Delete</Btn>
      </div>
    );
    expect(screen.getByText('Stock')).toBeDefined();
    expect(screen.getByText('42')).toBeDefined();
    expect(screen.getByText('Nothing here')).toBeDefined();
    expect(screen.getByText('Save')).toBeDefined();
  });

  it('renders skeleton placeholders and toast/error shells', () => {
    const { container } = render(
      <ToastProvider>
        <ErrorBoundary>
          <Skeleton className="h-4" />
          <SkeletonCard />
          <SkeletonTable rows={2} cols={2} />
          <span>shop content</span>
        </ErrorBoundary>
      </ToastProvider>
    );
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
    expect(screen.getByText('shop content')).toBeDefined();
  });

  it('error boundary shows the fallback when a child throws', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const Boom = () => {
      throw new Error('kaboom');
    };
    render(
      <ErrorBoundary fallback={<div>fallback view</div>}>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText('fallback view')).toBeDefined();
  });
});
