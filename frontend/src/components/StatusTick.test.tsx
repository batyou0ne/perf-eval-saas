import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusTick, type TickStatus } from './StatusTick';

/** The tick is the only thing carrying status in the task list and the dashboard, so
 * each state has to be tellable apart by shape — not just by colour. */
describe('StatusTick', () => {
  it('names its status for screen readers', () => {
    render(<StatusTick status="in_progress" />);
    expect(screen.getByRole('img', { name: 'In progress' })).toBeInTheDocument();
  });

  it('draws an empty box for work that has not started', () => {
    const { container } = render(<StatusTick status="todo" />);
    const tick = screen.getByRole('img', { name: 'To do' });

    expect(tick).toHaveClass('text-muted-foreground');
    expect(tick.style.background).toBe('');
    expect(container.querySelectorAll('span span')).toHaveLength(0);
  });

  it('half-fills the box while work is in progress', () => {
    const tick = render(<StatusTick status="in_progress" />).container.firstElementChild as HTMLElement;

    expect(tick).toHaveClass('text-status-warn');
    expect(tick.style.background).toContain('linear-gradient(to top, currentColor 50%, transparent 50%)');
  });

  it('fills the box and adds a check once work is done', () => {
    const { container } = render(<StatusTick status="done" />);
    const tick = screen.getByRole('img', { name: 'Done' });

    expect(tick).toHaveClass('bg-status-good');
    // The check mark is a rotated corner drawn in the card colour.
    expect(container.querySelector('span > span')).toHaveClass('rotate-[-45deg]');
  });

  it('strikes the box through when work is cancelled', () => {
    const { container } = render(<StatusTick status="cancelled" />);
    const tick = screen.getByRole('img', { name: 'Cancelled' });

    expect(tick).toHaveClass('text-status-bad');
    expect(container.querySelector('span > span')).toHaveClass('rotate-45');
  });

  it('renders every status without collapsing two of them into the same box', () => {
    const statuses: TickStatus[] = ['todo', 'in_progress', 'done', 'cancelled', 'not_started', 'submitted'];
    const { container } = render(
      <>
        {statuses.map((s) => (
          <StatusTick key={s} status={s} />
        ))}
      </>,
    );

    expect(container.querySelectorAll('[role="img"]')).toHaveLength(statuses.length);
  });
});
