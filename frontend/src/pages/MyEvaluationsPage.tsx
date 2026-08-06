import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson } from '@/lib/api';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const PAGE_SIZE = 20;

interface EvaluationSummary {
  id: string;
  cycle_name: string;
  subject_name: string;
  evaluator_id: string;
  type: 'self' | 'manager';
  status: 'not_started' | 'in_progress' | 'submitted';
}

interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

function cardTitle(e: EvaluationSummary, currentUserId: string | undefined): string {
  if (e.type === 'self') return 'Self-evaluation';
  if (e.evaluator_id === currentUserId) return `Evaluate ${e.subject_name}`;
  return 'Manager review';
}

export function MyEvaluationsPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<EvaluationSummary> | null>(null);

  useEffect(() => {
    setData(null);
    apiFetchJson<Page<EvaluationSummary>>(`/api/v1/evaluations/me?page=${page}&page_size=${PAGE_SIZE}`).then(
      setData,
    );
  }, [page]);

  if (data === null) return <p className="text-sm text-muted-foreground">Loading…</p>;

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-foreground">My Evaluations</h1>
      {data.items.length === 0 && <p className="text-sm text-muted-foreground">No evaluations yet.</p>}
      <div className="flex flex-col gap-3">
        {data.items.map((e) => {
          // A subject can only open their manager-eval once it's submitted (see can_view_evaluation).
          const isAwaitingManager = e.type === 'manager' && e.evaluator_id !== user?.id && e.status !== 'submitted';

          const card = (
            <Card>
              <CardHeader>
                <CardTitle>{cardTitle(e, user?.id)}</CardTitle>
                <CardAction>
                  <span className="text-sm capitalize text-muted-foreground">
                    {isAwaitingManager ? 'Awaiting manager' : e.status.replace('_', ' ')}
                  </span>
                </CardAction>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{e.cycle_name}</CardContent>
            </Card>
          );

          if (isAwaitingManager) return <div key={e.id}>{card}</div>;
          return (
            <Link key={e.id} to={`/evaluations/${e.id}`}>
              {card}
            </Link>
          );
        })}
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button variant="outline" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
