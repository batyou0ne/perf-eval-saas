import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';

export function ProtectedRoute() {
  const { status } = useAuth();

  if (status === 'loading') {
    return <div className="flex min-h-svh items-center justify-center text-muted-foreground">Loading…</div>;
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
