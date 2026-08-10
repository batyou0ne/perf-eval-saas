import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

type Row = typeof employee;

function page(items: Row[], total = items.length) {
  return { items, total, page: 1, page_size: 20 };
}

/** The page reads a paginated list and an unpaginated picker feed, so route by URL. */
function respondWith({ rows, options }: { rows: Row[]; options: Row[] }) {
  mockApiFetchJson.mockImplementation((path: string) =>
    Promise.resolve(path.includes('/users/options') ? options.map((o) => ({ id: o.id, full_name: o.full_name })) : page(rows)),
  );
}

describe('TeamPage', () => {
  beforeEach(() => {
    mockApiFetchJson.mockReset();
    mockUseAuth.mockReturnValue({ user: { id: ADMIN_ID } } as ReturnType<typeof useAuth>);
  });

  // A deactivated manager can never log in to complete the evaluation, so offering
  // them here would silently create an unsubmittable one. The backend rejects it too.
  it('does not offer inactive users as manager candidates', async () => {
    respondWith({ rows: [employee, activeManager, inactiveManager], options: [employee, activeManager] });

    render(<TeamPage />);
    await screen.findByRole('heading', { name: 'Team' });

    expect(screen.getAllByRole('option', { name: 'Active Manager' }).length).toBeGreaterThan(0);
    expect(screen.queryByRole('option', { name: /Inactive Manager/ })).not.toBeInTheDocument();
  });

  // The picker feed is active-only, so a leftover inactive manager has no option of its
  // own — without the fallback the select would render blank instead of the real value.
  it('still lists an already-assigned inactive manager so the current selection renders', async () => {
    respondWith({
      rows: [{ ...employee, manager_id: inactiveManager.id }, activeManager, inactiveManager],
      options: [employee, activeManager],
    });

    render(<TeamPage />);
    await screen.findByRole('heading', { name: 'Team' });

    expect(screen.getByRole('option', { name: 'Inactive Manager (inactive)' })).toBeInTheDocument();
  });

  // Deactivating hands the user's reports up to their skip-level manager, so rows other
  // than the clicked one change server-side. Patching a single row would leave them stale.
  it('re-fetches the team after a deactivation so handed-over rows update', async () => {
    const user = userEvent.setup();
    const skipLevel = { ...activeManager, id: 'skip-1', full_name: 'Skip Level' };
    const before = [{ ...employee, manager_id: activeManager.id }, activeManager, skipLevel];
    const after = [{ ...employee, manager_id: skipLevel.id }, { ...activeManager, is_active: false }, skipLevel];

    let deactivated = false;
    mockApiFetchJson.mockImplementation((path: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        deactivated = true;
        return Promise.resolve({ ...activeManager, is_active: false });
      }
      const rows = deactivated ? after : before;
      if (path.includes('/users/options')) {
        return Promise.resolve(rows.filter((r) => r.is_active).map((r) => ({ id: r.id, full_name: r.full_name })));
      }
      return Promise.resolve(page(rows));
    });

    render(<TeamPage />);
    await screen.findByRole('heading', { name: 'Team' });

    await user.click(screen.getAllByRole('button', { name: 'Deactivate' })[0]);

    expect(await screen.findByText(/Active Manager/)).toBeInTheDocument();
    const [reportRowSelect] = screen.getAllByRole('combobox');
    expect(reportRowSelect).toHaveValue(skipLevel.id);
  });
});
