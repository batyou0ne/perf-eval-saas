import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
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
  const [companies, setCompanies] = useState<Company[]>([]);

  const refetchCompanies = useCallback(() => {
    if (!isSuperAdmin) return;
    apiFetchJson<Company[]>('/api/v1/companies')
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

      {isSuperAdmin && <CreateCompanyForm onCreated={refetchCompanies} />}
      {(user?.role === 'company_admin' || isSuperAdmin) && (
        <InviteTeammateForm isSuperAdmin={isSuperAdmin} companies={companies} />
      )}
    </div>
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
        <CardDescription>No email sending yet — the invite link is shown here to copy/share.</CardDescription>
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
