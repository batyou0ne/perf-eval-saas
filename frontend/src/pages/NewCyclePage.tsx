import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetchJson, ApiError } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { CycleForm, type CycleFormValues } from '@/components/CycleForm';

export function NewCyclePage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(values: CycleFormValues) {
    setError(null);
    setSubmitting(true);
    try {
      const cycle = await apiFetchJson<{ id: string }>('/api/v1/cycles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...values,
          questions: values.questions.map((q, i) => ({ ...q, order: i })),
        }),
      });
      navigate(`/cycles/${cycle.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create cycle');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-foreground">New review cycle</h1>
      <Card>
        <CardContent>
          <CycleForm
            onSubmit={handleSubmit}
            submitLabel="Create cycle"
            submittingLabel="Creating…"
            submitting={submitting}
            error={error}
          />
        </CardContent>
      </Card>
    </div>
  );
}
