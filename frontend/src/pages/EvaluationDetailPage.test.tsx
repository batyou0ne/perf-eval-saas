import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { apiFetchJson, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { EvaluationDetailPage } from './EvaluationDetailPage';

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

const MANAGER_ID = 'manager-1';
const EMPLOYEE_ID = 'employee-1';

const baseEvaluation = {
  id: 'eval-1',
  cycle_id: 'cycle-1',
  cycle_name: 'H1 2026',
  subject_id: EMPLOYEE_ID,
  subject_name: 'Employee One',
  evaluator_id: MANAGER_ID,
  evaluator_name: 'Manager One',
  type: 'manager' as const,
  questions: [{ id: 'q1', text: 'How is communication?', type: 'rating' as const, order: 1 }],
  responses: [
    { question_id: 'q1', question_text: 'How is communication?', question_type: 'rating' as const, rating_value: 4, text_value: null },
  ],
  completed_tasks: [] as { id: string; title: string; completed_at: string }[],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/evaluations/eval-1']}>
      <Routes>
        <Route path="/evaluations/:id" element={<EvaluationDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('EvaluationDetailPage', () => {
  it('shows the fill-out form when the user is the evaluator', async () => {
    mockUseAuth.mockReturnValue({ user: { id: MANAGER_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue({ ...baseEvaluation, status: 'in_progress' });

    renderPage();

    expect(await screen.findByText('Evaluating Employee One')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit evaluation/i })).toBeInTheDocument();
  });

  // Regression for 79123e2: the subject of a manager-eval must see "Manager review"
  // (not "Evaluating {self}"), and must not be able to fill it out before it's submitted.
  it('shows "Manager review" and no form when the user is the subject and it is not yet submitted', async () => {
    mockUseAuth.mockReturnValue({ user: { id: EMPLOYEE_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue({ ...baseEvaluation, status: 'in_progress' });

    renderPage();

    expect(await screen.findByText('Manager review')).toBeInTheDocument();
    expect(screen.getByText(/waiting on manager one/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /submit evaluation/i })).not.toBeInTheDocument();
  });

  // "Draft saved" used to stick around after further edits, implying the newest
  // answer was persisted when it hadn't been sent yet.
  it('retracts the "Draft saved" confirmation once an answer changes again', async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({ user: { id: MANAGER_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue({ ...baseEvaluation, status: 'in_progress' });

    renderPage();
    await screen.findByText('Evaluating Employee One');

    await user.click(screen.getByRole('button', { name: /save draft/i }));
    expect(await screen.findByText('Draft saved')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '3' }));

    expect(screen.queryByText('Draft saved')).not.toBeInTheDocument();
  });

  it('shows the recorded responses instead of the form once the manager-eval is submitted', async () => {
    mockUseAuth.mockReturnValue({ user: { id: EMPLOYEE_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockImplementation((path: string) =>
      path.includes('/summary')
        ? Promise.reject(new ApiError(404, 'No summary yet'))
        : Promise.resolve({ ...baseEvaluation, status: 'submitted' })
    );

    renderPage();

    expect(await screen.findByText('Manager review')).toBeInTheDocument();
    expect(screen.getByText('How is communication?')).toBeInTheDocument();
    expect(screen.getByText('4 / 5')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /submit evaluation/i })).not.toBeInTheDocument();
  });

  it('shows the completed-tasks panel when the subject finished work during the cycle', async () => {
    mockUseAuth.mockReturnValue({ user: { id: MANAGER_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue({
      ...baseEvaluation,
      status: 'in_progress',
      completed_tasks: [{ id: 'task-1', title: 'Shipped the onboarding flow', completed_at: '2026-02-10T00:00:00Z' }],
    });

    renderPage();

    expect(await screen.findByText('Completed tasks this period')).toBeInTheDocument();
    expect(screen.getByText('Shipped the onboarding flow')).toBeInTheDocument();
  });

  it('omits the completed-tasks panel when there are none', async () => {
    mockUseAuth.mockReturnValue({ user: { id: MANAGER_ID } } as ReturnType<typeof useAuth>);
    mockApiFetchJson.mockResolvedValue({ ...baseEvaluation, status: 'in_progress' });

    renderPage();
    await screen.findByText('Evaluating Employee One');

    expect(screen.queryByText('Completed tasks this period')).not.toBeInTheDocument();
  });
});
