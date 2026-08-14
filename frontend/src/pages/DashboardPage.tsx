import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
import type { Page } from '@/lib/pagination';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

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
        <p className="text-sm text-muted-foreground">{user?.role.replace('_', ' ')}</p>
      </div>

      {!isSuperAdmin && <PendingWorkCard />}
      {canManageCycles && <ActiveCycleCard />}

      {isSuperAdmin && <CreateCompanyForm onCreated={refetchCompanies} />}
      {(user?.role === 'company_admin' || isSuperAdmin) && (
        <InviteTeammateForm isSuperAdmin={isSuperAdmin} companies={companies} />
      )}
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
  due_date: string | null;
}

interface PendingItem {
  key: string;
  kind: 'Evaluation' | 'Task';
  label: string;
  context: string;
  deadline: string | null;
  href: string;
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
      }));
      const taskItems: PendingItem[] = tasks.items.map((t) => ({
        key: `task-${t.id}`,
        kind: 'Task',
        label: t.title,
        context: 'Task',
        deadline: t.due_date,
        href: `/tasks/${t.id}`,
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
              className="flex items-center justify-between gap-4 border-b pb-3 last:border-b-0 last:pb-0"
            >
              <div>
                <p className="text-sm text-foreground">{item.label}</p>
                <p className="text-xs text-muted-foreground">
                  {item.kind} · {item.context}
                </p>
              </div>
              {item.deadline && <span className="text-xs text-muted-foreground">Due {item.deadline}</span>}
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
            <p className="text-xs text-muted-foreground">
              {cycle.start_date} – {cycle.end_date}
            </p>
            {progress && (
              <div className="flex flex-wrap gap-x-6 gap-y-1">
                <p className="text-sm text-foreground">
                  Self-evaluations:{' '}
                  <span className="font-medium">
                    {progress.self_submitted}/{progress.self_total}
                  </span>{' '}
                  submitted
                </p>
                <p className="text-sm text-foreground">
                  Manager evaluations:{' '}
                  <span className="font-medium">
                    {progress.manager_submitted}/{progress.manager_total}
                  </span>{' '}
                  submitted
                </p>
              </div>
            )}
          </>
        )}
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
