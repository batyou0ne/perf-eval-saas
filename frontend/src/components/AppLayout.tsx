import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';

export function AppLayout() {
  const { user, logout } = useAuth();
  const canManage = user?.role === 'company_admin' || user?.role === 'hr';
  const isCompanyAdmin = user?.role === 'company_admin';
  // Tasks are a per-company concern — super_admin has no company_id and the API rejects them.
  const canUseTasks = user?.role !== 'super_admin';

  return (
    <div className="min-h-svh">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <nav className="flex items-center gap-4">
          <Link to="/" className="font-semibold text-foreground">
            Performance Eval SaaS
          </Link>
          <Link to="/evaluations" className="text-sm text-muted-foreground hover:text-foreground">
            My Evaluations
          </Link>
          {canUseTasks && (
            <Link to="/tasks" className="text-sm text-muted-foreground hover:text-foreground">
              Tasks
            </Link>
          )}
          {canManage && (
            <>
              <Link to="/cycles" className="text-sm text-muted-foreground hover:text-foreground">
                Review Cycles
              </Link>
              <Link to="/team" className="text-sm text-muted-foreground hover:text-foreground">
                Team
              </Link>
            </>
          )}
          {isCompanyAdmin && (
            <Link to="/invites" className="text-sm text-muted-foreground hover:text-foreground">
              Invites
            </Link>
          )}
        </nav>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{user?.full_name}</span>
          <Button variant="outline" size="sm" onClick={() => logout()}>
            Log out
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl p-6">
        <Outlet />
      </main>
    </div>
  );
}
