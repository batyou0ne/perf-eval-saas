import { useEffect, useState } from 'react';
import { useOutletContext, useParams } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusTick, TICK_LABEL } from '@/components/StatusTick';
import type { TasksOutletContext } from '@/pages/TasksPage';

interface TaskDetail {
  id: string;
  title: string;
  description: string | null;
  created_by_id: string;
  created_by_name: string;
  assignee_id: string | null;
  assignee_name: string | null;
  status: 'todo' | 'in_progress' | 'done' | 'cancelled';
  due_date: string | null;
  claimed_at: string | null;
  completed_at: string | null;
}

export function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  // null outside the tasks master-detail layout (e.g. this component's own tests) — the
  // list-refresh callback is an enhancement for that layout, not something to depend on.
  const outletContext = useOutletContext<TasksOutletContext>();
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  function load() {
    if (!id) return;
    apiFetchJson<TaskDetail>(`/api/v1/tasks/${id}`)
      .then(setTask)
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : 'Could not load task'));
  }

  useEffect(load, [id]);

  async function runAction(action: () => Promise<TaskDetail>) {
    setActionError(null);
    setWorking(true);
    try {
      setTask(await action());
      outletContext?.onTaskChanged();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not update task');
    } finally {
      setWorking(false);
    }
  }

  if (loadError) return <p className="text-sm text-destructive">{loadError}</p>;
  if (!task) return <p className="text-sm text-muted-foreground">Loading…</p>;

  const isMine = task.assignee_id === user?.id;
  const canWork = isMine && task.status !== 'done' && task.status !== 'cancelled';

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-xs text-muted-foreground">Task</p>
        <h1 className="text-xl font-semibold text-foreground">{task.title}</h1>
        <p className="text-sm text-muted-foreground">Created by {task.created_by_name}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ownership</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <StatusTick status={task.status} />
            {isMine ? (
              <p className="text-sm font-medium text-primary">This task is yours.</p>
            ) : task.assignee_name ? (
              <p className="text-sm text-muted-foreground">Currently held by {task.assignee_name}.</p>
            ) : (
              <p className="text-sm text-muted-foreground">Sitting in the pool — nobody has claimed it yet.</p>
            )}
          </div>

          {actionError && <p className="text-sm text-destructive">{actionError}</p>}

          <div className="flex flex-wrap gap-2">
            {task.assignee_id === null && (
              <Button
                type="button"
                size="sm"
                disabled={working}
                onClick={() => runAction(() => apiFetchJson(`/api/v1/tasks/${task.id}/claim`, { method: 'POST' }))}
              >
                Claim this task
              </Button>
            )}
            {isMine && task.status !== 'done' && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={working}
                onClick={() =>
                  runAction(() => apiFetchJson(`/api/v1/tasks/${task.id}/release`, { method: 'POST' }))
                }
              >
                Release back to pool
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">{task.description || 'No description.'}</p>
          {task.due_date && (
            <p className="text-sm text-muted-foreground">
              Due <span className="font-mono">{task.due_date}</span>
            </p>
          )}
          <p className="flex items-center gap-2 text-sm text-foreground">
            <StatusTick status={task.status} />
            Status: {TICK_LABEL[task.status]}
          </p>

          {canWork && (
            <div className="flex flex-wrap gap-2">
              {task.status === 'todo' && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={working}
                  onClick={() =>
                    runAction(() =>
                      apiFetchJson(`/api/v1/tasks/${task.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: 'in_progress' }),
                      }),
                    )
                  }
                >
                  Start work
                </Button>
              )}
              <Button
                type="button"
                size="sm"
                disabled={working}
                onClick={() =>
                  runAction(() =>
                    apiFetchJson(`/api/v1/tasks/${task.id}`, {
                      method: 'PATCH',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ status: 'done' }),
                    }),
                  )
                }
              >
                Mark done
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
