import { useEffect, useState } from 'react';
import { apiFetchJson, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { PAGE_SIZE, totalPages, type Page } from '@/lib/pagination';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Pager } from '@/components/Pager';

interface TeamUser {
  id: string;
  full_name: string;
  email: string;
  role: string;
  manager_id: string | null;
  is_active: boolean;
}

/** Every active colleague, from the unpaginated picker feed — a manager on another page
 *  still has to be selectable. */
interface ManagerOption {
  id: string;
  full_name: string;
}

const USERS_PAGE = (page: number) => `/api/v1/users?page=${page}&page_size=${PAGE_SIZE}`;

export function TeamPage() {
  const { user: currentUser } = useAuth();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<TeamUser> | null>(null);
  const [options, setOptions] = useState<ManagerOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    apiFetchJson<Page<TeamUser>>(USERS_PAGE(page)).then(setData);
  }, [page]);

  useEffect(() => {
    apiFetchJson<ManagerOption[]>('/api/v1/users/options').then(setOptions);
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
      setData((current) =>
        current ? { ...current, items: current.items.map((u) => (u.id === userId ? updated : u)) } : current,
      );
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
      await apiFetchJson<TeamUser>(`/api/v1/users/${user.id}/${action}`, { method: 'POST' });
      // Deactivating hands this user's reports up to their own manager, so other rows
      // change too — and it also changes who can be picked as a manager.
      setData(await apiFetchJson<Page<TeamUser>>(USERS_PAGE(page)));
      setOptions(await apiFetchJson<ManagerOption[]>('/api/v1/users/options'));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update user status');
    } finally {
      setSavingId(null);
    }
  }

  if (!data) return <p className="text-sm text-muted-foreground">Loading…</p>;

  const optionsById = new Map(options.map((o) => [o.id, o.full_name]));
  const nameFor = (id: string) =>
    optionsById.get(id) ?? data.items.find((u) => u.id === id)?.full_name ?? 'Unknown user';

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-foreground">Team</h1>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Card>
        <CardHeader>
          <CardTitle>Set managers</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {data.items.map((u) => (
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
                  {/* The picker feed is active-only, so an inactive manager left over from
                      older data has no option to select — surface it or the select renders blank. */}
                  {u.manager_id && !optionsById.has(u.manager_id) && (
                    <option value={u.manager_id}>{nameFor(u.manager_id)} (inactive)</option>
                  )}
                  {options
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
      <Pager page={page} totalPages={totalPages(data)} onPageChange={setPage} />
    </div>
  );
}
