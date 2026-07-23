import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetchJson, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Question {
  id: string;
  text: string;
  type: 'rating' | 'text';
  order: number;
}

interface CycleDetail {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: 'draft' | 'active' | 'closed';
  questions: Question[];
}

export function CycleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [cycle, setCycle] = useState<CycleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState(false);

  useEffect(() => {
    if (!id) return;
    apiFetchJson<CycleDetail>(`/api/v1/cycles/${id}`).then(setCycle);
  }, [id]);

  async function handleActivate() {
    if (!id) return;
    setError(null);
    setActivating(true);
    try {
      const updated = await apiFetchJson<{ status: CycleDetail['status'] }>(`/api/v1/cycles/${id}/activate`, {
        method: 'POST',
      });
      setCycle((current) => (current ? { ...current, status: updated.status } : current));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not activate cycle');
    } finally {
      setActivating(false);
    }
  }

  if (!cycle) return <p className="text-sm text-muted-foreground">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">{cycle.name}</h1>
          <p className="text-sm text-muted-foreground">
            {cycle.start_date} – {cycle.end_date} · <span className="capitalize">{cycle.status}</span>
          </p>
        </div>
        {cycle.status === 'draft' && (
          <Button onClick={handleActivate} disabled={activating}>
            {activating ? 'Activating…' : 'Activate cycle'}
          </Button>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader>
          <CardTitle>Questions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {cycle.questions.map((q) => (
            <div key={q.id} className="flex items-center justify-between border-b pb-2 last:border-b-0 last:pb-0">
              <span className="text-sm text-foreground">{q.text}</span>
              <span className="text-xs capitalize text-muted-foreground">{q.type}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      {cycle.status === 'active' && (
        <p className="text-sm text-muted-foreground">
          This cycle is active — self and manager evaluations have been generated for everyone in the company.
        </p>
      )}
    </div>
  );
}
