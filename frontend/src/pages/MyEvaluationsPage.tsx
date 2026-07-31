import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson } from '@/lib/api';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface EvaluationSummary {
  id: string;
  cycle_name: string;
  subject_name: string;
  evaluator_id: string;
  type: 'self' | 'manager';
  status: 'not_started' | 'in_progress' | 'submitted';
}

function cardTitle(e: EvaluationSummary, currentUserId: string | undefined): string {
  if (e.type === 'self') return 'Self-evaluation';
  if (e.evaluator_id === currentUserId) return `Evaluate ${e.subject_name}`;
  return 'Manager review';
}

export function MyEvaluationsPage() {
  const { user } = useAuth();
  const [evaluations, setEvaluations] = useState<EvaluationSummary[] | null>(null);

  useEffect(() => {
    apiFetchJson<EvaluationSummary[]>('/api/v1/evaluations/me').then(setEvaluations);
  }, []);

  if (evaluations === null) return <p className="text-sm text-muted-foreground">Loading…</p>;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-foreground">My Evaluations</h1>
      {evaluations.length === 0 && <p className="text-sm text-muted-foreground">No evaluations yet.</p>}
      <div className="flex flex-col gap-3">
        {evaluations.map((e) => {
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
    </div>
  );
}
