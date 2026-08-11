import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
import { PAGE_SIZE, totalPages, type Page } from '@/lib/pagination';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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

export function TasksPage() {
  const { user } = useAuth();
  const [scope, setScope] = useState<Scope>('all');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<TaskSummary> | null>(null);
  const [assignees, setAssignees] = useState<Assignee[]>([]);

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

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-foreground">Tasks</h1>

      <CreateTaskForm assignees={assignees} onCreated={refetch} />

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
        <div className="flex flex-col gap-3">
          {data.items.length === 0 && <p className="text-sm text-muted-foreground">No tasks here.</p>}
          {data.items.map((t) => (
            <Link key={t.id} to={`/tasks/${t.id}`}>
              <Card>
                <CardHeader>
                  <CardTitle>{t.title}</CardTitle>
                  <CardAction>
                    <span className="text-sm text-muted-foreground">{STATUS_LABEL[t.status]}</span>
                  </CardAction>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {t.assignee_name ? `Assigned to ${t.assignee_name}` : 'In the pool'}
                  {t.due_date && ` · Due ${t.due_date}`}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {data && <Pager page={page} totalPages={totalPages(data)} onPageChange={setPage} />}
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
