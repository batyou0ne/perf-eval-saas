import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiFetchJson } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface CycleSummary {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: 'draft' | 'active' | 'closed';
}

export function CyclesPage() {
  const [cycles, setCycles] = useState<CycleSummary[] | null>(null);

  useEffect(() => {
    apiFetchJson<CycleSummary[]>('/api/v1/cycles').then(setCycles);
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Review Cycles</h1>
        <Link to="/cycles/new">
          <Button>New cycle</Button>
        </Link>
      </div>

      {cycles === null && <p className="text-sm text-muted-foreground">Loading…</p>}
      {cycles?.length === 0 && <p className="text-sm text-muted-foreground">No cycles yet.</p>}

      <div className="flex flex-col gap-3">
        {cycles?.map((cycle) => (
          <Link key={cycle.id} to={`/cycles/${cycle.id}`}>
            <Card>
              <CardHeader>
                <CardTitle>{cycle.name}</CardTitle>
                <CardAction>
                  <span className="text-sm capitalize text-muted-foreground">{cycle.status}</span>
                </CardAction>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {cycle.start_date} – {cycle.end_date}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
