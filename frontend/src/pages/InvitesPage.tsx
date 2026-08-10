import { useEffect, useState } from 'react';
import { apiFetchJson, ApiError } from '@/lib/api';
import { PAGE_SIZE, totalPages, type Page } from '@/lib/pagination';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Pager } from '@/components/Pager';

interface InviteRow {
  id: string;
  email: string;
  role: string;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
}

const INVITES_PAGE = (page: number) => `/api/v1/invites?page=${page}&page_size=${PAGE_SIZE}`;

type InviteStatus = 'pending' | 'accepted' | 'expired';

function statusOf(invite: InviteRow): InviteStatus {
  if (invite.accepted_at) return 'accepted';
  if (new Date(invite.expires_at) < new Date()) return 'expired';
  return 'pending';
}

export function InvitesPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<InviteRow> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [resentLink, setResentLink] = useState<{ id: string; link: string } | null>(null);

  function refetch() {
    return apiFetchJson<Page<InviteRow>>(INVITES_PAGE(page)).then(setData);
  }

  useEffect(() => {
    apiFetchJson<Page<InviteRow>>(INVITES_PAGE(page)).then(setData);
  }, [page]);

  async function handleCancel(id: string) {
    setError(null);
    setBusyId(id);
    try {
      await apiFetchJson(`/api/v1/invites/${id}`, { method: 'DELETE' });
      // Removing a row pulls later pages forward, so re-read rather than splicing locally.
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not cancel invite');
    } finally {
      setBusyId(null);
    }
  }

  async function handleResend(id: string) {
    setError(null);
    setResentLink(null);
    setBusyId(id);
    try {
      const resent = await apiFetchJson<{ invite_link: string }>(`/api/v1/invites/${id}/resend`, { method: 'POST' });
      setResentLink({ id, link: resent.invite_link });
      await refetch();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not resend invite');
    } finally {
      setBusyId(null);
    }
  }

  if (!data) return <p className="text-sm text-muted-foreground">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-foreground">Invites</h1>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Card>
        <CardHeader>
          <CardTitle>Sent invites</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {data.items.length === 0 && <p className="text-sm text-muted-foreground">No invites yet.</p>}
          {data.items.map((invite) => {
            const status = statusOf(invite);
            return (
              <div key={invite.id} className="flex flex-col gap-2 border-b pb-3 last:border-b-0 last:pb-0">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm text-foreground">{invite.email}</p>
                    <p className="text-xs capitalize text-muted-foreground">
                      {invite.role.replace('_', ' ')} · <span className="capitalize">{status}</span>
                    </p>
                  </div>
                  {status !== 'accepted' && (
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={busyId === invite.id}
                        onClick={() => handleResend(invite.id)}
                      >
                        Resend
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={busyId === invite.id}
                        onClick={() => handleCancel(invite.id)}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
                {resentLink?.id === invite.id && (
                  <p className="break-all rounded-md bg-muted p-2 text-sm text-muted-foreground">{resentLink.link}</p>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>
      <Pager page={page} totalPages={totalPages(data)} onPageChange={setPage} />
    </div>
  );
}
