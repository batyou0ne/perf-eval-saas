import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetchJson } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { TeamPage } from './TeamPage';

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

const ADMIN_ID = 'admin-1';

const employee = {
  id: 'employee-1',
  full_name: 'Eddie Employee',
  email: 'eddie@acme.io',
  role: 'employee',
  manager_id: null as string | null,
  is_active: true,
};
const activeManager = {
  id: 'manager-1',
  full_name: 'Active Manager',
  email: 'active@acme.io',
  role: 'manager',
  manager_id: null,
  is_active: true,
};
const inactiveManager = {
  id: 'manager-2',
  full_name: 'Inactive Manager',
  email: 'inactive@acme.io',
  role: 'manager',
  manager_id: null,
  is_active: false,
};

describe('TeamPage', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ user: { id: ADMIN_ID } } as ReturnType<typeof useAuth>);
  });

  // A deactivated manager can never log in to complete the evaluation, so offering
  // them here would silently create an unsubmittable one. The backend rejects it too.
  it('does not offer inactive users as manager candidates', async () => {
    mockApiFetchJson.mockResolvedValue([employee, activeManager, inactiveManager]);

    render(<TeamPage />);
    // The heading only renders once the user list has loaded; the names themselves
    // appear both as row labels and as options, so they're ambiguous to wait on.
    await screen.findByRole('heading', { name: 'Team' });

    expect(screen.getAllByRole('option', { name: 'Active Manager' }).length).toBeGreaterThan(0);
    expect(screen.queryByRole('option', { name: /Inactive Manager/ })).not.toBeInTheDocument();
  });

  it('still lists an already-assigned inactive manager so the current selection renders', async () => {
    mockApiFetchJson.mockResolvedValue([
      { ...employee, manager_id: inactiveManager.id },
      activeManager,
      inactiveManager,
    ]);

    render(<TeamPage />);
    // The heading only renders once the user list has loaded; the names themselves
    // appear both as row labels and as options, so they're ambiguous to wait on.
    await screen.findByRole('heading', { name: 'Team' });

    expect(screen.getByRole('option', { name: 'Inactive Manager (inactive)' })).toBeInTheDocument();
  });
});
