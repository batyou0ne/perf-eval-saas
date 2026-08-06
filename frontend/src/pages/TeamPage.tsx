import { useEffect, useState } from 'react';
import { apiFetchJson, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface TeamUser {
  id: string;
  full_name: string;
  email: string;
  role: string;
  manager_id: string | null;
  is_active: boolean;
}

export function TeamPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<TeamUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => {
    apiFetchJson<TeamUser[]>('/api/v1/users').then(setUsers);
  }, []);

  async function handleManagerChange(userId: string, managerId: string) {
    setError(null);
    setSavingId(userId);
    try {
      const updated = await apiFetchJson<TeamUser>(`/api/v1/users/${userId}/manager`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manager_id: managerId || null }),
      });
      setUsers((current) => current?.map((u) => (u.id === userId ? updated : u)) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not assign manager');
    } finally {
      setSavingId(null);
    }
  }

  async function handleToggleActive(user: TeamUser) {
    setError(null);
    setSavingId(user.id);
    try {
      const action = user.is_active ? 'deactivate' : 'reactivate';
      const updated = await apiFetchJson<TeamUser>(`/api/v1/users/${user.id}/${action}`, { method: 'POST' });
      setUsers((current) => current?.map((u) => (u.id === user.id ? updated : u)) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update user status');
    } finally {
      setSavingId(null);
    }
  }

  if (!users) return <p className="text-sm text-muted-foreground">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-foreground">Team</h1>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Card>
        <CardHeader>
          <CardTitle>Set managers</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {users.map((u) => (
            <div
              key={u.id}
              className={`flex items-center justify-between gap-4 border-b pb-3 last:border-b-0 last:pb-0 ${u.is_active ? '' : 'opacity-50'}`}
            >
              <div>
                <p className="text-sm text-foreground">
                  {u.full_name}
                  {!u.is_active && <span className="ml-2 text-xs font-normal text-muted-foreground">(inactive)</span>}
                </p>
                <p className="text-xs capitalize text-muted-foreground">{u.role.replace('_', ' ')}</p>
              </div>
              <div className="flex items-center gap-2">
                <select
                  className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
                  value={u.manager_id ?? ''}
                  disabled={savingId === u.id}
                  onChange={(e) => handleManagerChange(u.id, e.target.value)}
                >
                  <option value="">No manager</option>
                  {users
                    .filter((candidate) => candidate.id !== u.id)
                    .map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.full_name}
                      </option>
                    ))}
                </select>
                {u.id !== currentUser?.id && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={savingId === u.id}
                    onClick={() => handleToggleActive(u)}
                  >
                    {u.is_active ? 'Deactivate' : 'Reactivate'}
                  </Button>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
