import { useState, type FormEvent } from 'react';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <div className="mx-auto flex min-h-svh max-w-2xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Welcome, {user?.full_name}</h1>
          <p className="text-sm text-muted-foreground">{user?.role.replace('_', ' ')}</p>
        </div>
        <Button variant="outline" onClick={() => logout()}>
          Log out
        </Button>
      </div>

      {/* Company Admin only — inviting into other companies is a Super Admin / company-management
          feature that doesn't exist yet, so this form stays scoped to "invite into my own company". */}
      {user?.role === 'company_admin' && <InviteTeammateForm />}
    </div>
  );
}

const INVITABLE_ROLES = ['company_admin', 'manager', 'hr', 'employee'] as const;

function InviteTeammateForm() {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<(typeof INVITABLE_ROLES)[number]>('employee');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const data = await apiFetchJson<{ invite_link: string }>('/api/v1/invites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role }),
      });
      setResult(data.invite_link);
      setEmail('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create invite');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Invite a teammate</CardTitle>
        <CardDescription>No email sending yet — the invite link is shown here to copy/share.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="invite-email">Email</Label>
            <Input id="invite-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="invite-role">Role</Label>
            <select
              id="invite-role"
              className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
              value={role}
              onChange={(e) => setRole(e.target.value as (typeof INVITABLE_ROLES)[number])}
            >
              {INVITABLE_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
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
