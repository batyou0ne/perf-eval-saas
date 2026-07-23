import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiFetchJson } from '@/lib/api';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface EvaluationSummary {
  id: string;
  cycle_name: string;
  subject_name: string;
  type: 'self' | 'manager';
  status: 'not_started' | 'in_progress' | 'submitted';
}

export function MyEvaluationsPage() {
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
        {evaluations.map((e) => (
          <Link key={e.id} to={`/evaluations/${e.id}`}>
            <Card>
              <CardHeader>
                <CardTitle>{e.type === 'self' ? 'Self-evaluation' : `Evaluate ${e.subject_name}`}</CardTitle>
                <CardAction>
                  <span className="text-sm capitalize text-muted-foreground">{e.status.replace('_', ' ')}</span>
                </CardAction>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{e.cycle_name}</CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
