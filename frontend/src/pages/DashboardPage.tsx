import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
import type { Page } from '@/lib/pagination';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusTick, type TickStatus } from '@/components/StatusTick';
import { cn } from '@/lib/utils';

interface Company {
  id: string;
  name: string;
}

export function DashboardPage() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'super_admin';
  const canManageCycles = user?.role === 'company_admin' || user?.role === 'hr';
  const [companies, setCompanies] = useState<Company[]>([]);

  const refetchCompanies = useCallback(() => {
    if (!isSuperAdmin) return;
    // The picker feed rather than the paginated list: a company on page 2 still has to be
    // selectable when inviting its first admin.
    apiFetchJson<Company[]>('/api/v1/companies/options')
      .then(setCompanies)
      .catch(() => {});
  }, [isSuperAdmin]);

  useEffect(() => {
    refetchCompanies();
  }, [refetchCompanies]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Welcome, {user?.full_name}</h1>
        <p className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">
          {user?.role.replace('_', ' ')}
        </p>
      </div>

      {/* Pending work is why someone opens the app, so it takes the wide column and
          the standing figures sit beside it rather than below the fold. */}
      {!isSuperAdmin && (
        <div className="grid items-start gap-5 lg:grid-cols-[1.7fr_1fr]">
          <PendingWorkCard />
          <div className="flex flex-col gap-5">
            {canManageCycles && <ActiveCycleCard />}
            <CompletedTasksCard />
          </div>
        </div>
      )}

      {/* Admin forms stay in a reading-width column — a form stretched to the grid's
          full width is harder to fill in, not easier. */}
      <div className="flex max-w-2xl flex-col gap-6">
        {isSuperAdmin && <CreateCompanyForm onCreated={refetchCompanies} />}
        {(user?.role === 'company_admin' || isSuperAdmin) && (
          <InviteTeammateForm isSuperAdmin={isSuperAdmin} companies={companies} />
        )}
      </div>
    </div>
  );
}

interface EvaluationSummary {
  id: string;
  cycle_name: string;
  cycle_end_date: string;
  subject_id: string;
  subject_name: string;
  type: 'self' | 'manager';
}

interface TaskSummary {
  id: string;
  title: string;
  status: TickStatus;
  due_date: string | null;
}

interface PendingItem {
  key: string;
  kind: 'Evaluation' | 'Task';
  label: string;
  context: string;
  deadline: string | null;
  href: string;
  status: TickStatus;
}

function PendingWorkCard() {
  const [items, setItems] = useState<PendingItem[] | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetchJson<Page<EvaluationSummary>>('/api/v1/evaluations/me?pending=true&page_size=50'),
      apiFetchJson<Page<TaskSummary>>('/api/v1/tasks?scope=mine&open_only=true&page_size=50'),
    ]).then(([evaluations, tasks]) => {
      const evaluationItems: PendingItem[] = evaluations.items.map((e) => ({
        key: `eval-${e.id}`,
        kind: 'Evaluation',
        label: e.type === 'self' ? 'Self-evaluation' : `Evaluate ${e.subject_name}`,
        context: e.cycle_name,
        deadline: e.cycle_end_date,
        href: `/evaluations/${e.id}`,
        // The pending feed carries no evaluation status of its own — everything in it is,
        // by definition, still waiting to be started.
        status: 'not_started',
      }));
      const taskItems: PendingItem[] = tasks.items.map((t) => ({
        key: `task-${t.id}`,
        kind: 'Task',
        label: t.title,
        context: 'Task',
        deadline: t.due_date,
        href: `/tasks/${t.id}`,
        status: t.status,
      }));
      setItems(
        [...evaluationItems, ...taskItems].sort((a, b) => {
          if (!a.deadline) return 1;
          if (!b.deadline) return -1;
          return a.deadline.localeCompare(b.deadline);
        }),
      );
    });
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your pending work</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {items === null ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">You're all caught up — nothing waiting on you right now.</p>
        ) : (
          items.map((item) => (
            <Link
              key={item.key}
              to={item.href}
              className="flex items-center gap-3 border-b pb-3 last:border-b-0 last:pb-0"
            >
              <StatusTick status={item.status} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{item.label}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {item.kind} · {item.context}
                </p>
              </div>
              {item.deadline && (
                <span className="shrink-0 font-mono text-xs text-muted-foreground">due {item.deadline}</span>
              )}
            </Link>
          ))
        )}
      </CardContent>
    </Card>
  );
}

interface Cycle {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: 'draft' | 'active' | 'closed';
}

interface CycleProgress {
  self_submitted: number;
  self_total: number;
  manager_submitted: number;
  manager_total: number;
}

function ActiveCycleCard() {
  const [cycle, setCycle] = useState<Cycle | null | undefined>(undefined);
  const [progress, setProgress] = useState<CycleProgress | null>(null);

  useEffect(() => {
    apiFetchJson<Page<Cycle>>('/api/v1/cycles?page_size=100').then((page) => {
      setCycle(page.items.find((c) => c.status === 'active') ?? null);
    });
  }, []);

  useEffect(() => {
    if (!cycle) return;
    apiFetchJson<CycleProgress>(`/api/v1/cycles/${cycle.id}/progress`).then(setProgress);
  }, [cycle]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active review cycle</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {cycle === undefined ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : cycle === null ? (
          <p className="text-sm text-muted-foreground">
            No active cycle right now.{' '}
            <Link to="/cycles/new" className="underline">
              Start a new one
            </Link>
            .
          </p>
        ) : (
          <>
            <Link to={`/cycles/${cycle.id}`} className="text-sm font-medium text-foreground">
              {cycle.name}
            </Link>
            <p className="font-mono text-xs text-muted-foreground">
              {cycle.start_date} – {cycle.end_date}
            </p>
            {progress && (
              <div className="flex flex-col gap-3">
                <ProgressRow
                  label="Self-evaluations"
                  done={progress.self_submitted}
                  total={progress.self_total}
                />
                <ProgressRow
                  label="Manager evaluations"
                  done={progress.manager_submitted}
                  total={progress.manager_total}
                />
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/** A submitted count only means something next to the total it is a fraction of, so the
 * bar and the "4 / 7" readout always travel together. */
function ProgressRow({ label, done, total }: { label: string; done: number; total: number }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const complete = total > 0 && done === total;

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span className="text-foreground">{label}</span>
        <span className="font-mono text-muted-foreground">
          {done}/{total}
        </span>
      </div>
      {/* The hairline tone, not the sunken-paper one: an empty track has to stay
          visible on a white card, otherwise 0/7 reads as "no bar at all". */}
      <div className="h-1.5 overflow-hidden rounded-full bg-border">
        <div
          className={cn('h-full rounded-full', complete ? 'bg-status-good' : 'bg-primary')}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function CompletedTasksCard() {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    // Only the total is wanted, so ask for the smallest page the API will hand back.
    apiFetchJson<Page<TaskSummary>>('/api/v1/tasks?scope=mine&status=done&page_size=1')
      .then((p) => setCount(p.total))
      .catch(() => {});
  }, []);

  return (
    <Card>
      <CardContent className="flex flex-col gap-0.5">
        <span className="font-mono text-2xl font-bold text-foreground">{count ?? '—'}</span>
        <span className="text-xs text-muted-foreground">Tasks you've completed</span>
      </CardContent>
    </Card>
  );
}

function CreateCompanyForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const company = await apiFetchJson<Company>('/api/v1/companies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      setSuccess(`Created "${company.name}". Invite its first admin below.`);
      setName('');
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create company');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create a company</CardTitle>
        <CardDescription>Onboard a new customer company onto the platform.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="company-name">Company name</Label>
            <Input id="company-name" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {success && <p className="text-sm text-muted-foreground">{success}</p>}
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Creating…' : 'Create company'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

const COMPANY_ADMIN_INVITABLE_ROLES = ['company_admin', 'manager', 'hr', 'employee'] as const;

function InviteTeammateForm({ isSuperAdmin, companies }: { isSuperAdmin: boolean; companies: Company[] }) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<(typeof COMPANY_ADMIN_INVITABLE_ROLES)[number]>('employee');
  const [companyId, setCompanyId] = useState('');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setCompanyId((current) => (companies.some((c) => c.id === current) ? current : companies[0]?.id || ''));
  }, [companies]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const body: Record<string, string> = { email, role: isSuperAdmin ? 'company_admin' : role };
      if (isSuperAdmin) body.company_id = companyId;
      const data = await apiFetchJson<{ invite_link: string }>('/api/v1/invites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      setResult(data.invite_link);
      setEmail('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create invite');
    } finally {
      setSubmitting(false);
    }
  }

  if (isSuperAdmin && companies.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Invite a company admin</CardTitle>
          <CardDescription>Create a company first — there's nothing to invite someone into yet.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isSuperAdmin ? 'Invite a company admin' : 'Invite a teammate'}</CardTitle>
        <CardDescription>
          We'll email them an invite link. It's also shown here after sending, so you can share it directly.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="invite-email">Email</Label>
            <Input id="invite-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>

          {isSuperAdmin ? (
            <div className="flex flex-col gap-2">
              <Label htmlFor="invite-company">Company</Label>
              <select
                id="invite-company"
                className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
              >
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <Label htmlFor="invite-role">Role</Label>
              <select
                id="invite-role"
                className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
                value={role}
                onChange={(e) => setRole(e.target.value as (typeof COMPANY_ADMIN_INVITABLE_ROLES)[number])}
              >
                {COMPANY_ADMIN_INVITABLE_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
          {result && <p className="break-all rounded-md bg-muted p-2 text-sm text-muted-foreground">{result}</p>}
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Sending…' : 'Send invite'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
