import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, Outlet, useParams } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
import { PAGE_SIZE, totalPages, type Page } from '@/lib/pagination';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Pager } from '@/components/Pager';

interface TaskSummary {
  id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done' | 'cancelled';
  assignee_id: string | null;
  assignee_name: string | null;
  due_date: string | null;
}

interface Assignee {
  id: string;
  full_name: string;
}

type Scope = 'all' | 'pool' | 'mine';

const TABS: { scope: Scope; label: string }[] = [
  { scope: 'all', label: 'All' },
  { scope: 'pool', label: 'Pool' },
  { scope: 'mine', label: 'Mine' },
];

const STATUS_LABEL: Record<TaskSummary['status'], string> = {
  todo: 'To do',
  in_progress: 'In progress',
  done: 'Done',
  cancelled: 'Cancelled',
};

/** Lets the nested detail pane (rendered via <Outlet>) tell the list to refetch after
 * a claim/release/status change, so the two panes never show contradictory state. */
export interface TasksOutletContext {
  onTaskChanged: () => void;
}

export function TasksPage() {
  const { user } = useAuth();
  // Also matches when the nested detail route is active — React Router merges a nested
  // route's params into every ancestor's useParams() for the same location.
  const { id: selectedId } = useParams<{ id?: string }>();
  const [scope, setScope] = useState<Scope>('all');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<TaskSummary> | null>(null);
  const [assignees, setAssignees] = useState<Assignee[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const refetch = useCallback(() => {
    setData(null);
    apiFetchJson<Page<TaskSummary>>(`/api/v1/tasks?scope=${scope}&page=${page}&page_size=${PAGE_SIZE}`).then(
      setData,
    );
  }, [scope, page]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  useEffect(() => {
    const source =
      user?.role === 'company_admin' || user?.role === 'hr'
        ? '/api/v1/users/options'
        : user?.role === 'manager'
          ? '/api/v1/users/reports'
          : null;
    if (!source) {
      setAssignees([]);
      return;
    }
    apiFetchJson<Assignee[]>(source)
      .then(setAssignees)
      .catch(() => setAssignees([]));
  }, [user?.role]);

  function handleScopeChange(next: Scope) {
    setScope(next);
    setPage(1);
  }

  function handleCreated() {
    setShowCreateForm(false);
    refetch();
  }

  return (
    <div className="flex gap-6">
      <div className="flex w-80 shrink-0 flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-xl font-semibold text-foreground">Tasks</h1>
          <Button type="button" size="sm" onClick={() => setShowCreateForm((v) => !v)}>
            {showCreateForm ? 'Cancel' : 'New task'}
          </Button>
        </div>

        {showCreateForm && <CreateTaskForm assignees={assignees} onCreated={handleCreated} />}

        <div className="flex gap-2">
          {TABS.map((t) => (
            <Button
              key={t.scope}
              type="button"
              size="sm"
              variant={scope === t.scope ? 'default' : 'outline'}
              onClick={() => handleScopeChange(t.scope)}
            >
              {t.label}
            </Button>
          ))}
        </div>

        {data === null ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="flex flex-col overflow-hidden rounded-xl ring-1 ring-foreground/10">
            {data.items.length === 0 && <p className="px-4 py-3 text-sm text-muted-foreground">No tasks here.</p>}
            {data.items.map((t) => (
              <Link
                key={t.id}
                to={`/tasks/${t.id}`}
                className={cn(
                  'flex flex-col gap-1 border-b px-4 py-3 text-sm last:border-b-0 hover:bg-muted/50',
                  t.id === selectedId && 'bg-muted',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium text-foreground">{t.title}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{STATUS_LABEL[t.status]}</span>
                </div>
                <span className="truncate text-xs text-muted-foreground">
                  {t.assignee_name ? `Assigned to ${t.assignee_name}` : 'In the pool'}
                  {t.due_date && ` · Due ${t.due_date}`}
                </span>
              </Link>
            ))}
          </div>
        )}

        {data && <Pager page={page} totalPages={totalPages(data)} onPageChange={setPage} />}
      </div>

      <div className="min-w-0 flex-1">
        {selectedId ? (
          <Outlet context={{ onTaskChanged: refetch } satisfies TasksOutletContext} />
        ) : (
          <div className="flex h-64 items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground">
            Select a task to see its details.
          </div>
        )}
      </div>
    </div>
  );
}

function CreateTaskForm({ assignees, onCreated }: { assignees: Assignee[]; onCreated: () => void }) {
  const { user } = useAuth();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [assigneeChoice, setAssigneeChoice] = useState('pool');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const assigneeId = assigneeChoice === 'pool' ? null : assigneeChoice === 'self' ? user?.id : assigneeChoice;
      await apiFetchJson('/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description: description || null,
          due_date: dueDate || null,
          assignee_id: assigneeId,
        }),
      });
      setTitle('');
      setDescription('');
      setDueDate('');
      setAssigneeChoice('pool');
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create task');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>New task</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="task-title">Title</Label>
            <Input id="task-title" required value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="task-description">Description</Label>
            <textarea
              id="task-description"
              className="min-h-16 rounded-lg border border-input bg-transparent p-2.5 text-sm"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="task-due-date">Due date</Label>
            <Input
              id="task-due-date"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="task-assignee">Assign to</Label>
            <select
              id="task-assignee"
              className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
              value={assigneeChoice}
              onChange={(e) => setAssigneeChoice(e.target.value)}
            >
              <option value="pool">Leave in the pool</option>
              <option value="self">Myself</option>
              {assignees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.full_name}
                </option>
              ))}
            </select>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Creating…' : 'Create task'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
