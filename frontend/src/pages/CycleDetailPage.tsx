import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetchJson, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CycleForm, type CycleFormValues } from '@/components/CycleForm';

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

type EvaluationStatus = 'not_started' | 'in_progress' | 'submitted';

interface SubjectProgress {
  subject_id: string;
  subject_name: string;
  self_status: EvaluationStatus;
  manager_status: EvaluationStatus | null;
}

interface CycleProgress {
  self_submitted: number;
  self_total: number;
  manager_submitted: number;
  manager_total: number;
  subjects: SubjectProgress[];
}

function formatStatus(status: EvaluationStatus): string {
  return status.replace('_', ' ');
}

export function CycleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [cycle, setCycle] = useState<CycleDetail | null>(null);
  const [progress, setProgress] = useState<CycleProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState(false);
  const [closing, setClosing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    apiFetchJson<CycleDetail>(`/api/v1/cycles/${id}`).then(setCycle);
  }, [id]);

  useEffect(() => {
    if (!id || !cycle || cycle.status === 'draft') return;
    apiFetchJson<CycleProgress>(`/api/v1/cycles/${id}/progress`).then(setProgress);
  }, [id, cycle?.status]);

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

  async function handleClose() {
    if (!id) return;
    setError(null);
    setClosing(true);
    try {
      const updated = await apiFetchJson<{ status: CycleDetail['status'] }>(`/api/v1/cycles/${id}/close`, {
        method: 'POST',
      });
      setCycle((current) => (current ? { ...current, status: updated.status } : current));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not close cycle');
    } finally {
      setClosing(false);
    }
  }

  async function handleSave(values: CycleFormValues) {
    if (!id) return;
    setSaveError(null);
    setSaving(true);
    try {
      const updated = await apiFetchJson<CycleDetail>(`/api/v1/cycles/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...values,
          questions: values.questions.map((q, i) => ({ ...q, order: i })),
        }),
      });
      setCycle(updated);
      setIsEditing(false);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : 'Could not update cycle');
    } finally {
      setSaving(false);
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
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setIsEditing((current) => !current)}>
              {isEditing ? 'Cancel edit' : 'Edit'}
            </Button>
            <Button onClick={handleActivate} disabled={activating}>
              {activating ? 'Activating…' : 'Activate cycle'}
            </Button>
          </div>
        )}
        {cycle.status === 'active' && (
          <Button variant="outline" onClick={handleClose} disabled={closing}>
            {closing ? 'Closing…' : 'Close cycle'}
          </Button>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {isEditing ? (
        <Card>
          <CardHeader>
            <CardTitle>Edit cycle</CardTitle>
          </CardHeader>
          <CardContent>
            <CycleForm
              initialValues={{
                name: cycle.name,
                start_date: cycle.start_date,
                end_date: cycle.end_date,
                questions: cycle.questions.map((q) => ({ text: q.text, type: q.type })),
              }}
              onSubmit={handleSave}
              submitLabel="Save changes"
              submittingLabel="Saving…"
              submitting={saving}
              error={saveError}
            />
          </CardContent>
        </Card>
      ) : (
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
      )}

      {cycle.status === 'active' && (
        <p className="text-sm text-muted-foreground">
          This cycle is active — self and manager evaluations have been generated for everyone in the company.
        </p>
      )}

      {cycle.status === 'closed' && (
        <p className="text-sm text-muted-foreground">
          This cycle is closed — evaluations are read-only and can no longer be edited or submitted.
        </p>
      )}

      {cycle.status !== 'draft' && (
        <Card>
          <CardHeader>
            <CardTitle>Progress</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {!progress ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : (
              <>
                <div className="flex flex-wrap gap-x-6 gap-y-1">
                  <p className="text-sm text-foreground">
                    Self-evaluations:{' '}
                    <span className="font-medium">
                      {progress.self_submitted}/{progress.self_total}
                    </span>{' '}
                    submitted
                  </p>
                  <p className="text-sm text-foreground">
                    Manager evaluations:{' '}
                    <span className="font-medium">
                      {progress.manager_submitted}/{progress.manager_total}
                    </span>{' '}
                    submitted
                  </p>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="grid grid-cols-3 gap-4 text-xs font-medium text-muted-foreground">
                    <span>Employee</span>
                    <span>Self-eval</span>
                    <span>Manager eval</span>
                  </div>
                  {progress.subjects.map((s) => (
                    <div
                      key={s.subject_id}
                      className="grid grid-cols-3 items-center gap-4 border-b pb-2 text-sm last:border-b-0 last:pb-0"
                    >
                      <span className="text-foreground">{s.subject_name}</span>
                      <span className="capitalize text-muted-foreground">{formatStatus(s.self_status)}</span>
                      <span className="capitalize text-muted-foreground">
                        {s.manager_status ? formatStatus(s.manager_status) : 'No manager'}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
