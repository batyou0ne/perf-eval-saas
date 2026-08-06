import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { apiFetchJson } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { MyEvaluationsPage } from './MyEvaluationsPage';

vi.mock('@/lib/api', () => ({ apiFetchJson: vi.fn() }));
vi.mock('@/lib/auth-context', () => ({ useAuth: vi.fn() }));

const mockApiFetchJson = vi.mocked(apiFetchJson);
const mockUseAuth = vi.mocked(useAuth);

const MANAGER_ID = 'manager-1';
const EMPLOYEE_ID = 'employee-1';

function renderPage() {
  return render(
    <MemoryRouter>
      <MyEvaluationsPage />
    </MemoryRouter>
  );
}

function page(items: unknown[]) {
  return { items, total: items.length, page: 1, page_size: 20 };
}

describe('MyEvaluationsPage', () => {
  it('labels a self-evaluation as "Self-evaluation"', async () => {
    mockUseAuth.mockReturnValue({ user: { id: EMPLOYEE_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue(
      page([
        {
          id: 'eval-1',
          cycle_name: 'H1 2026',
          subject_name: 'Employee One',
          evaluator_id: EMPLOYEE_ID,
          type: 'self',
          status: 'in_progress',
        },
      ]),
    );

    renderPage();

    expect(await screen.findByText('Self-evaluation')).toBeInTheDocument();
  });

  it('labels a manager-eval as "Evaluate {subject}" and links to it when the user is the evaluator', async () => {
    mockUseAuth.mockReturnValue({ user: { id: MANAGER_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue(
      page([
        {
          id: 'eval-2',
          cycle_name: 'H1 2026',
          subject_name: 'Employee One',
          evaluator_id: MANAGER_ID,
          type: 'manager',
          status: 'not_started',
        },
      ]),
    );

    renderPage();

    expect(await screen.findByText('Evaluate Employee One')).toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute('href', '/evaluations/eval-2');
  });

  // Regression for 79123e2: EvaluationSummary now carries evaluator_id, and the
  // subject of a manager-eval must see "Manager review" (not "Evaluate {self}"),
  // with the card locked until the manager submits.
  it('labels a manager-eval as "Manager review" and locks the card when the user is the subject and it is not yet submitted', async () => {
    mockUseAuth.mockReturnValue({ user: { id: EMPLOYEE_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue(
      page([
        {
          id: 'eval-3',
          cycle_name: 'H1 2026',
          subject_name: 'Employee One',
          evaluator_id: MANAGER_ID,
          type: 'manager',
          status: 'in_progress',
        },
      ]),
    );

    renderPage();

    expect(await screen.findByText('Manager review')).toBeInTheDocument();
    expect(screen.getByText('Awaiting manager')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('unlocks the card for the subject once the manager-eval is submitted', async () => {
    mockUseAuth.mockReturnValue({ user: { id: EMPLOYEE_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue(
      page([
        {
          id: 'eval-4',
          cycle_name: 'H1 2026',
          subject_name: 'Employee One',
          evaluator_id: MANAGER_ID,
          type: 'manager',
          status: 'submitted',
        },
      ]),
    );

    renderPage();

    expect(await screen.findByText('Manager review')).toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute('href', '/evaluations/eval-4');
  });
});
