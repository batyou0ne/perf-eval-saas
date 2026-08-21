import type { ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';

/** A hairline compass rose — the calibration idea in miniature, and the only
 * decorative mark in the app. */
function BrandMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" className="text-primary">
      <circle cx="9" cy="9" r="7" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M9 2v3M9 13v3M2 9h3M13 9h3" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="9" cy="9" r="1.6" fill="currentColor" />
    </svg>
  );
}

function NavItem({ to, children }: { to: string; children: ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `border-b-2 py-1 text-sm transition-colors ${
          isActive
            ? 'border-primary font-medium text-foreground'
            : 'border-transparent text-muted-foreground hover:text-foreground'
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const canManage = user?.role === 'company_admin' || user?.role === 'hr';
  const isCompanyAdmin = user?.role === 'company_admin';
  // Tasks are a per-company concern — super_admin has no company_id and the API rejects them.
  const canUseTasks = user?.role !== 'super_admin';
  // The tasks master-detail layout and the dashboard's two-column grid both need more
  // room than the app's usual single reading column.
  const isTasksPage = location.pathname.startsWith('/tasks');
  const isDashboard = location.pathname === '/';

  return (
    <div className="min-h-svh">
      <header className="flex items-center justify-between border-b bg-card px-6 py-4">
        <nav className="flex items-center gap-5">
          <Link to="/" className="flex items-center gap-2 font-semibold text-foreground">
            <BrandMark />
            Performance Eval SaaS
          </Link>
          <NavItem to="/evaluations">My Evaluations</NavItem>
          {canUseTasks && <NavItem to="/tasks">Tasks</NavItem>}
          {canManage && (
            <>
              <NavItem to="/cycles">Review Cycles</NavItem>
              <NavItem to="/team">Team</NavItem>
            </>
          )}
          {isCompanyAdmin && <NavItem to="/invites">Invites</NavItem>}
        </nav>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{user?.full_name}</span>
          <Button variant="outline" size="sm" onClick={() => logout()}>
            Log out
          </Button>
        </div>
      </header>
      <main className={`mx-auto p-6 ${isTasksPage ? 'max-w-6xl' : isDashboard ? 'max-w-5xl' : 'max-w-3xl'}`}>
        <Outlet />
      </main>
    </div>
  );
}
