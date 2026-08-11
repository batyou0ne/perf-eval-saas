import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetchJson } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { TasksPage } from './TasksPage';

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
  status: 'todo' as const,
  assignee_id: null,
  assignee_name: null,
  due_date: null,
};
const mineTask = {
  id: 'task-2',
  title: 'Write the onboarding doc',
  status: 'in_progress' as const,
  assignee_id: USER_ID,
  assignee_name: 'Eddie Employee',
  due_date: null,
};

function page(items: (typeof poolTask)[]) {
  return { items, total: items.length, page: 1, page_size: 20 };
}

describe('TasksPage', () => {
  beforeEach(() => {
    mockApiFetchJson.mockReset();
    mockUseAuth.mockReturnValue({ user: { id: USER_ID, role: 'employee' } } as ReturnType<typeof useAuth>);
  });

  it('renders the pool list', async () => {
    mockApiFetchJson.mockImplementation((path: string) => {
      if (path.startsWith('/api/v1/tasks')) return Promise.resolve(page([poolTask]));
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter>
        <TasksPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Fix the API route mismatch')).toBeInTheDocument();
    expect(screen.getByText(/In the pool/)).toBeInTheDocument();
  });

  it('requests scope=mine when the Mine tab is selected', async () => {
    const user = userEvent.setup();
    const calls: string[] = [];
    mockApiFetchJson.mockImplementation((path: string) => {
      if (path.startsWith('/api/v1/tasks')) {
        calls.push(path);
        return Promise.resolve(path.includes('scope=mine') ? page([mineTask]) : page([poolTask]));
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter>
        <TasksPage />
      </MemoryRouter>,
    );
    await screen.findByText('Fix the API route mismatch');

    await user.click(screen.getByRole('button', { name: 'Mine' }));

    expect(await screen.findByText('Write the onboarding doc')).toBeInTheDocument();
    expect(calls.some((c) => c.includes('scope=mine'))).toBe(true);
  });
});
