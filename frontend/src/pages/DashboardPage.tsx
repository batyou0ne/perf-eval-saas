import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
import type { Page } from '@/lib/pagination';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusTick, TICK_LABEL, type TickStatus } from '@/components/StatusTick';
import { cn } from '@/lib/utils';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

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

      {/* Standing shape of the company, for the people who steer it. It sits below the
          personal cards because it answers "how are we doing", not "what do I do next". */}
      {canManageCycles && <AnalyticsSection />}

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

const TASK_SLICES = ['todo', 'in_progress', 'done', 'cancelled'] as const;
type TaskSlice = (typeof TASK_SLICES)[number];

interface AnalyticsOverview {
  task_status_counts: Record<TaskSlice, number>;
  // null, not 0: the cycle owed no evaluations of that type, so there is no rate to plot.
  cycle_completion_rates: { cycle_name: string; self_pct: number | null; manager_pct: number | null }[];
}

/** Which design token each chart colour comes from, and the light-theme value to fall
 * back on when there is no computed style to read (jsdom under test). */
const CHART_TOKENS = {
  todo: ['--muted-foreground', 'oklch(0.551 0.027 264.4)'],
  in_progress: ['--status-warn', 'oklch(0.621 0.111 75.3)'],
  done: ['--status-good', 'oklch(0.531 0.079 159.9)'],
  cancelled: ['--status-bad', 'oklch(0.537 0.135 31.1)'],
  self: ['--primary', 'oklch(0.388 0.081 256.5)'],
  manager: ['--status-good', 'oklch(0.531 0.079 159.9)'],
  axis: ['--muted-foreground', 'oklch(0.551 0.027 264.4)'],
} as const satisfies Record<string, readonly [string, string]>;

type ChartColors = Record<keyof typeof CHART_TOKENS, string>;

const FALLBACK_COLORS = Object.fromEntries(
  Object.entries(CHART_TOKENS).map(([key, [, fallback]]) => [key, fallback]),
) as ChartColors;

/** Recharts puts these straight onto SVG `fill`/`stroke` attributes, where `var(--token)`
 * doesn't resolve — so the charts need real colour strings rather than token references.
 * Resolving them at runtime keeps the charts on the app's palette instead of a second,
 * hand-copied one, and means a theme swap moves them too. */
function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(FALLBACK_COLORS);

  useEffect(() => {
    const read = () => {
      const root = getComputedStyle(document.documentElement);
      setColors(
        Object.fromEntries(
          Object.entries(CHART_TOKENS).map(([key, [cssVar, fallback]]) => [
            key,
            root.getPropertyValue(cssVar).trim() || fallback,
          ]),
        ) as ChartColors,
      );
    };

    read();

    // The palette is swapped by toggling `.dark` on <html>, which changes what the
    // tokens resolve to without re-rendering anything. Without this the charts would
    // keep whichever theme's colours they happened to mount under.
    const observer = new MutationObserver(read);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  return colors;
}

function AnalyticsSection() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const colors = useChartColors();

  useEffect(() => {
    apiFetchJson<AnalyticsOverview>('/api/v1/analytics/overview')
      .then(setData)
      .catch(() => {});
  }, []);

  const sliceCounts = data?.task_status_counts;
  const totalTasks = sliceCounts ? TASK_SLICES.reduce((sum, slice) => sum + sliceCounts[slice], 0) : 0;
  const pieData = sliceCounts ? TASK_SLICES.map((slice) => ({ slice, value: sliceCounts[slice] })) : [];

  return (
    <div className="grid items-start gap-5 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Task breakdown</CardTitle>
          <CardDescription>Every task in the company, by status.</CardDescription>
        </CardHeader>
        <CardContent>
          {!data ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : totalTasks === 0 ? (
            <p className="text-sm text-muted-foreground">No tasks have been created yet.</p>
          ) : (
            <div className="flex flex-col items-center gap-4 sm:flex-row">
              <ResponsiveContainer width="100%" height={180} minWidth={0} className="sm:max-w-[180px]">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="slice" innerRadius={45} outerRadius={72} paddingAngle={2}>
                    {pieData.map((entry) => (
                      <Cell key={entry.slice} fill={colors[entry.slice]} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value, name) => [value as number, TICK_LABEL[name as TaskSlice]]} />
                </PieChart>
              </ResponsiveContainer>

              {/* The counts live in real DOM rather than only in the SVG, so the numbers
                  stay readable to a screen reader and selectable like any other text. */}
              <ul className="flex w-full flex-col gap-2">
                {TASK_SLICES.map((slice) => (
                  <li key={slice} className="flex items-center gap-2 text-xs">
                    <span
                      aria-hidden
                      className="size-2.5 shrink-0 rounded-[3px]"
                      style={{ backgroundColor: colors[slice] }}
                    />
                    <span className="flex-1 text-foreground">{TICK_LABEL[slice]}</span>
                    <span className="font-mono text-muted-foreground">{sliceCounts![slice]}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Evaluation completion by cycle</CardTitle>
          <CardDescription>Share of evaluations submitted, oldest cycle first.</CardDescription>
        </CardHeader>
        <CardContent>
          {!data ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : data.cycle_completion_rates.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No cycle has generated evaluations yet — activate one to start tracking completion.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={220} minWidth={0}>
              <BarChart data={data.cycle_completion_rates} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid vertical={false} stroke={colors.axis} strokeOpacity={0.2} />
                <XAxis
                  dataKey="cycle_name"
                  tick={{ fill: colors.axis, fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: colors.axis, strokeOpacity: 0.3 }}
                  // Cycle names are free text ("Q1 2026 Performance Review"), so they get
                  // clipped to keep the axis one line rather than rotated into a wedge.
                  tickFormatter={(name: string) => (name.length > 12 ? `${name.slice(0, 12)}…` : name)}
                />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 25, 50, 75, 100]}
                  tick={{ fill: colors.axis, fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => `${value}%`}
                />
                <Tooltip formatter={(value) => `${value}%`} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="self_pct" name="Self" fill={colors.self} radius={[3, 3, 0, 0]} maxBarSize={28} />
                <Bar dataKey="manager_pct" name="Manager" fill={colors.manager} radius={[3, 3, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
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
