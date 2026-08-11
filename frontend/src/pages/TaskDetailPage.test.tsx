import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { apiFetchJson } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { TaskDetailPage } from './TaskDetailPage';

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

const USER_ID = 'employee-1';

const poolTask = {
  id: 'task-1',
  title: 'Fix the API route mismatch',
  description: 'The endpoint changed name.',
  created_by_id: 'employee-2',
  created_by_name: 'Other Employee',
  assignee_id: null,
  assignee_name: null,
  status: 'todo' as const,
  due_date: null,
  claimed_at: null,
  completed_at: null,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/tasks/task-1']}>
      <Routes>
        <Route path="/tasks/:id" element={<TaskDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('TaskDetailPage', () => {
  it('claiming a pool task shows the ownership badge', async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({ user: { id: USER_ID, role: 'employee' } } as ReturnType<typeof useAuth>);

    let claimed = false;
    mockApiFetchJson.mockImplementation((path: string, init?: RequestInit) => {
      if (path.endsWith('/claim')) {
        claimed = true;
        return Promise.resolve({ ...poolTask, assignee_id: USER_ID, assignee_name: 'Eddie Employee' });
      }
      void init;
      return Promise.resolve(claimed ? { ...poolTask, assignee_id: USER_ID, assignee_name: 'Eddie Employee' } : poolTask);
    });

    renderPage();
    await screen.findByText('Sitting in the pool — nobody has claimed it yet.');

    await user.click(screen.getByRole('button', { name: 'Claim this task' }));

    expect(await screen.findByText('This task is yours.')).toBeInTheDocument();
    expect(mockApiFetchJson).toHaveBeenCalledWith('/api/v1/tasks/task-1/claim', { method: 'POST' });
  });
});
