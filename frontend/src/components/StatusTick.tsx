import { cn } from '@/lib/utils';

/** Task statuses and evaluation statuses share `in_progress`, and both read the same
 * way on screen, so one tick serves both rather than two near-identical components. */
export type TickStatus = 'todo' | 'in_progress' | 'done' | 'cancelled' | 'not_started' | 'submitted';

export const TICK_LABEL: Record<TickStatus, string> = {
  todo: 'To do',
  in_progress: 'In progress',
  done: 'Done',
  cancelled: 'Cancelled',
  not_started: 'Not started',
  submitted: 'Submitted',
};

const TONE: Record<TickStatus, string> = {
  todo: 'text-muted-foreground',
  not_started: 'text-muted-foreground',
  in_progress: 'text-status-warn',
  done: 'text-status-good bg-status-good',
  submitted: 'text-status-good bg-status-good',
  cancelled: 'text-status-bad',
};

// Half-filled from the bottom, the way a gauge fills — the shape carries the meaning,
// so the ticks still read apart from each other without colour vision.
const HALF_FILL = 'linear-gradient(to top, currentColor 50%, transparent 50%)';

export function StatusTick({ status, className }: { status: TickStatus; className?: string }) {
  const isFilled = status === 'done' || status === 'submitted';

  return (
    <span
      role="img"
      aria-label={TICK_LABEL[status]}
      className={cn(
        'relative inline-flex size-3.5 shrink-0 items-center justify-center rounded-[3px] border-[1.5px] border-current',
        TONE[status],
        className,
      )}
      style={status === 'in_progress' ? { background: HALF_FILL } : undefined}
    >
      {isFilled && (
        <span className="h-[3.5px] w-[6px] -translate-y-px rotate-[-45deg] border-b-[1.5px] border-l-[1.5px] border-card" />
      )}
      {status === 'cancelled' && (
        <span className="absolute inset-[2px] rotate-45 border-t-[1.5px] border-current" />
      )}
    </span>
  );
}
