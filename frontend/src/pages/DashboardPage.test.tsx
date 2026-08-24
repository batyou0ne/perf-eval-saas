import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetchJson } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { DashboardPage } from './DashboardPage';

vi.mock('@/lib/api', () => ({
  apiFetchJson: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));
vi.mock('@/lib/auth-context', () => ({ useAuth: vi.fn() }));

const mockApiFetchJson = vi.mocked(apiFetchJson);
const mockUseAuth = vi.mocked(useAuth);

function page<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: 50 };
}

function respondByPath(handlers: Record<string, unknown>) {
  mockApiFetchJson.mockImplementation((path: string) => {
    const match = Object.entries(handlers).find(([prefix]) => path.startsWith(prefix));
    if (!match) return Promise.reject(new Error(`Unhandled path in test: ${path}`));
    return Promise.resolve(match[1]);
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe('DashboardPage', () => {
  beforeEach(() => {
    mockApiFetchJson.mockReset();
  });

  it("shows an employee's pending evaluation and task, soonest deadline first", async () => {
    mockUseAuth.mockReturnValue({ user: { id: 'emp-1', full_name: 'Eddie Employee', role: 'employee' } } as ReturnType<
      typeof useAuth
    >);
    respondByPath({
      '/api/v1/evaluations/me': page([
        {
          id: 'eval-1',
          cycle_name: 'H1 2026',
          cycle_end_date: '2026-06-30',
          subject_id: 'emp-1',
          subject_name: 'Eddie Employee',
          type: 'self',
        },
      ]),
      '/api/v1/tasks': page([{ id: 'task-1', title: 'Fix the API route mismatch', status: 'in_progress', due_date: '2026-02-01' }]),
    });

    renderPage();

    const taskRow = await screen.findByText('Fix the API route mismatch');
    const evalRow = screen.getByText('Self-evaluation');
    // Task is due earlier (2026-02-01) than the evaluation (2026-06-30), so it sorts first.
    expect(taskRow.compareDocumentPosition(evalRow) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows the caught-up empty state when nothing is pending', async () => {
    mockUseAuth.mockReturnValue({ user: { id: 'emp-1', full_name: 'Eddie', role: 'employee' } } as ReturnType<
      typeof useAuth
    >);
    respondByPath({ '/api/v1/evaluations/me': page([]), '/api/v1/tasks': page([]) });

    renderPage();

    expect(await screen.findByText(/all caught up/i)).toBeInTheDocument();
  });

  it('shows the active-cycle progress card for a company admin', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'admin-1', full_name: 'Selin Admin', role: 'company_admin' },
    } as ReturnType<typeof useAuth>);
    respondByPath({
      '/api/v1/evaluations/me': page([]),
      '/api/v1/tasks': page([]),
      '/api/v1/cycles/cycle-1/progress': { self_submitted: 3, self_total: 7, manager_submitted: 1, manager_total: 4 },
      '/api/v1/cycles': page([
        { id: 'cycle-1', name: 'August 2026 Check-in', start_date: '2026-08-01', end_date: '2026-08-31', status: 'active' },
      ]),
      '/api/v1/companies/options': [],
    });

    renderPage();

    expect(await screen.findByText('August 2026 Check-in')).toBeInTheDocument();
    expect(await screen.findByText('3/7')).toBeInTheDocument();
    expect(screen.getByText('1/4')).toBeInTheDocument();
  });

  it('shows the analytics charts for a company admin, with a count per task status', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'admin-1', full_name: 'Selin Admin', role: 'company_admin' },
    } as ReturnType<typeof useAuth>);
    respondByPath({
      '/api/v1/evaluations/me': page([]),
      '/api/v1/tasks': page([]),
      '/api/v1/cycles': page([]),
      '/api/v1/companies/options': [],
      '/api/v1/analytics/overview': {
        task_status_counts: { todo: 12, in_progress: 5, done: 34, cancelled: 2 },
        cycle_completion_rates: [
          { cycle_name: 'Q1 2026', self_pct: 85, manager_pct: 72 },
          { cycle_name: 'Q2 2026', self_pct: 100, manager_pct: null },
        ],
      },
    });

    renderPage();

    expect(await screen.findByText('Task breakdown')).toBeInTheDocument();
    expect(screen.getByText('Evaluation completion by cycle')).toBeInTheDocument();
    // The legend carries the numbers in real DOM — the chart itself is an SVG that
    // jsdom never gives a width to, so there is nothing to assert inside it.
    const legendRow = screen.getByText('In progress').closest('li');
    expect(legendRow).toHaveTextContent('5');
    expect(screen.getByText('Done').closest('li')).toHaveTextContent('34');
  });

  it('tells a company admin when there is nothing to chart yet', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'hr-1', full_name: 'HR Person', role: 'hr' },
    } as ReturnType<typeof useAuth>);
    respondByPath({
      '/api/v1/evaluations/me': page([]),
      '/api/v1/tasks': page([]),
      '/api/v1/cycles': page([]),
      '/api/v1/analytics/overview': {
        task_status_counts: { todo: 0, in_progress: 0, done: 0, cancelled: 0 },
        cycle_completion_rates: [],
      },
    });

    renderPage();

    expect(await screen.findByText(/no tasks have been created yet/i)).toBeInTheDocument();
    expect(screen.getByText(/no cycle has generated evaluations yet/i)).toBeInTheDocument();
  });

  it('hides the analytics charts from an employee', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'emp-1', full_name: 'Eddie Employee', role: 'employee' },
    } as ReturnType<typeof useAuth>);
    respondByPath({ '/api/v1/evaluations/me': page([]), '/api/v1/tasks': page([]) });

    renderPage();

    // Wait for the page to settle so this isn't just asserting on an unrendered frame.
    expect(await screen.findByText(/all caught up/i)).toBeInTheDocument();
    expect(screen.queryByText('Task breakdown')).not.toBeInTheDocument();
    expect(screen.queryByText('Evaluation completion by cycle')).not.toBeInTheDocument();
    // respondByPath rejects unhandled paths, so an analytics fetch here would have
    // surfaced as a rejection rather than silently passing.
    expect(mockApiFetchJson).not.toHaveBeenCalledWith('/api/v1/analytics/overview');
  });

  it('prompts to start a cycle when none is active', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'hr-1', full_name: 'HR Person', role: 'hr' },
    } as ReturnType<typeof useAuth>);
    respondByPath({
      '/api/v1/evaluations/me': page([]),
      '/api/v1/tasks': page([]),
      '/api/v1/cycles': page([
        { id: 'cycle-0', name: 'Old cycle', start_date: '2026-01-01', end_date: '2026-03-31', status: 'closed' },
      ]),
    });

    renderPage();

    expect(await screen.findByText(/no active cycle/i)).toBeInTheDocument();
  });
});
