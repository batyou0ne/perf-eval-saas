import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';

export function AppLayout() {
  const { user, logout } = useAuth();
  const canManage = user?.role === 'company_admin' || user?.role === 'hr';

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
