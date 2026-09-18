import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ErrorBoundary } from '../components/ErrorBoundary';
import {
  Skeleton,
  SkeletonCard,
  SkeletonGrid,
  SkeletonTable,
  SkeletonText,
} from '../components/Skeleton';
import { ToastProvider, useToast } from '../components/Toast';
import {
  Badge,
  Btn,
  Card,
  Empty,
  Field,
  FormError,
  Input,
  PageTitle,
  SectionTitle,
  Select,
  Stat,
  TableWrap,
  ValidatedInput,
} from '../components/ui';

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

  it('shows the built-in fallback and recovers through "Try again"', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    let shouldThrow = true;
    const Flaky = () => {
      if (shouldThrow) throw new Error('boom');
      return <span>recovered</span>;
    };

    render(
      <ErrorBoundary>
        <Flaky />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeDefined();

    shouldThrow = false;
    fireEvent.click(screen.getByText('Try again'));
    expect(screen.getByText('recovered')).toBeDefined();
  });
});

describe('ui primitives', () => {
  it('renders every primitive, tone and button variant', () => {
    render(
      <div>
        <Card className="extra">card body</Card>
        <SectionTitle title="With sub" sub="subtitle" />
        <SectionTitle title="Without sub" />
        <Stat label="Emerald" value={1} sub="sub" accent="emerald" />
        <Stat label="Teal" value={2} accent="teal" />
        <Stat label="Amber" value={3} accent="amber" />
        <Stat label="Rose" value={4} accent="rose" />
        <Stat label="Indigo" value={5} accent="indigo" />
        <Stat label="Default accent" value={6} />
        <Btn variant="primary">primary</Btn>
        <Btn variant="secondary">secondary</Btn>
        <Btn variant="ghost">ghost</Btn>
        <Btn variant="danger">danger</Btn>
        <Btn>default variant</Btn>
        <Input placeholder="plain input" />
        <Select aria-label="currency">
          <option>BDT</option>
        </Select>
        <PageTitle title="Inventory" sub="levels" right={<button>add</button>} />
        <PageTitle title="Bare title" />
        <Badge>slate tone</Badge>
        <Badge tone="green">green</Badge>
        <Badge tone="red">red</Badge>
        <Badge tone="amber">amber</Badge>
        <Badge tone="blue">blue</Badge>
        <Field label="Email">
          <Input placeholder="email" />
        </Field>
        <Empty title="Nothing" sub="add something" />
        <Empty title="Bare empty" />
        <TableWrap>
          <table>
            <tbody>
              <tr>
                <td>row</td>
              </tr>
            </tbody>
          </table>
        </TableWrap>
        <FormError />
        <FormError message="Invalid" />
        <ValidatedInput placeholder="valid" />
        <ValidatedInput placeholder="invalid" error="Required" />
      </div>
    );

    expect(screen.getByText('card body')).toBeDefined();
    expect(screen.getByText('Without sub')).toBeDefined();
    expect(screen.getByText('default variant')).toBeDefined();
    expect(screen.getByLabelText('currency')).toBeDefined();
    expect(screen.getByText('add')).toBeDefined();
    expect(screen.getByText('Bare empty')).toBeDefined();
    expect(screen.getByText('row')).toBeDefined();
    expect(screen.getByText('Invalid')).toBeDefined();
    expect(screen.getByText('Required')).toBeDefined();
  });

  it('renders every skeleton variant', () => {
    const { container } = render(
      <div>
        <SkeletonText />
        <SkeletonText lines={1} className="mb-2" />
        <SkeletonGrid count={2} cols={2} />
        <SkeletonTable />
      </div>
    );

    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });
});

/** Drives every toast tone through the context, so the container is exercised. */
function ToastProbe() {
  const { notify, success, error, info, warning } = useToast();
  return (
    <div>
      <button onClick={() => notify('plain notice')}>notify</button>
      <button onClick={() => success('saved ok')}>success</button>
      <button onClick={() => error('save failed')}>error</button>
      <button onClick={() => info('for your information')}>info</button>
      <button onClick={() => warning('careful now')}>warning</button>
    </div>
  );
}

describe('ToastProvider', () => {
  it('renders each tone with its own icon', () => {
    render(
      <ToastProvider>
        <ToastProbe />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('success'));
    fireEvent.click(screen.getByText('error'));
    fireEvent.click(screen.getByText('info'));
    fireEvent.click(screen.getByText('warning'));

    expect(screen.getByText('saved ok')).toBeDefined();
    expect(screen.getByText('save failed')).toBeDefined();
    expect(screen.getByText('for your information')).toBeDefined();
    expect(screen.getByText('careful now')).toBeDefined();
  });

  it('dismisses a toast on click and clears it after four seconds', () => {
    vi.useFakeTimers();
    try {
      render(
        <ToastProvider>
          <ToastProbe />
        </ToastProvider>
      );

      fireEvent.click(screen.getByText('notify'));
      expect(screen.getByText('plain notice')).toBeDefined();

      // One toast is on screen, so the only close glyph belongs to it.
      fireEvent.click(screen.getByText('✕'));
      expect(screen.queryByText('plain notice')).toBeNull();

      fireEvent.click(screen.getByText('success'));
      expect(screen.getByText('saved ok')).toBeDefined();

      act(() => {
        vi.advanceTimersByTime(4000);
      });
      expect(screen.queryByText('saved ok')).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });
});
