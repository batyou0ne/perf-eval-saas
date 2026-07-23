import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import { apiFetchJson, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';

interface Question {
  id: string;
  text: string;
  type: 'rating' | 'text';
  order: number;
}

interface ResponseRead {
  question_id: string;
  question_text: string;
  question_type: 'rating' | 'text';
  rating_value: number | null;
  text_value: string | null;
}

interface EvaluationDetail {
  id: string;
  cycle_name: string;
  subject_name: string;
  evaluator_id: string;
  evaluator_name: string;
  type: 'self' | 'manager';
  status: 'not_started' | 'in_progress' | 'submitted';
  questions: Question[];
  responses: ResponseRead[];
}

type Answer = { rating_value?: number; text_value?: string };

export function EvaluationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [evaluation, setEvaluation] = useState<EvaluationDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!id) return;
    apiFetchJson<EvaluationDetail>(`/api/v1/evaluations/${id}`)
      .then(setEvaluation)
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : 'Could not load evaluation'));
  }, [id]);

  if (loadError) return <p className="text-sm text-destructive">{loadError}</p>;
  if (!evaluation) return <p className="text-sm text-muted-foreground">Loading…</p>;

  const canFillOut = user?.id === evaluation.evaluator_id && evaluation.status !== 'submitted';

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!id || !evaluation) return;
    setSubmitError(null);
    setSubmitting(true);
    try {
      const responses = evaluation.questions.map((q) => ({
        question_id: q.id,
        rating_value: answers[q.id]?.rating_value ?? null,
        text_value: answers[q.id]?.text_value ?? null,
      }));
      await apiFetchJson(`/api/v1/evaluations/${id}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ responses }),
      });
      navigate('/evaluations');
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : 'Could not submit evaluation');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">
          {evaluation.type === 'self' ? 'Self-evaluation' : `Evaluating ${evaluation.subject_name}`}
        </h1>
        <p className="text-sm text-muted-foreground">{evaluation.cycle_name}</p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-5">
          {canFillOut ? (
            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              {evaluation.questions.map((q) => (
                <div key={q.id} className="flex flex-col gap-2">
                  <Label>{q.text}</Label>
                  {q.type === 'rating' ? (
                    <div className="flex gap-2">
                      {[1, 2, 3, 4, 5].map((n) => {
                        const selected = answers[q.id]?.rating_value === n;
                        return (
                          <button
                            key={n}
                            type="button"
                            onClick={() => setAnswers((a) => ({ ...a, [q.id]: { rating_value: n } }))}
                            className={
                              'flex size-8 items-center justify-center rounded-lg border text-sm ' +
                              (selected
                                ? 'border-primary bg-primary text-primary-foreground'
                                : 'border-input text-foreground')
                            }
                          >
                            {n}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <textarea
                      className="min-h-20 rounded-lg border border-input bg-transparent p-2.5 text-sm"
                      value={answers[q.id]?.text_value ?? ''}
                      onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: { text_value: e.target.value } }))}
                    />
                  )}
                </div>
              ))}
              {submitError && <p className="text-sm text-destructive">{submitError}</p>}
              <Button type="submit" disabled={submitting}>
                {submitting ? 'Submitting…' : 'Submit evaluation'}
              </Button>
            </form>
          ) : evaluation.status === 'submitted' ? (
            <div className="flex flex-col gap-5">
              {evaluation.responses.map((r) => (
                <div key={r.question_id} className="flex flex-col gap-1">
                  <p className="text-sm font-medium text-foreground">{r.question_text}</p>
                  <p className="text-sm text-muted-foreground">
                    {r.question_type === 'rating' ? `${r.rating_value} / 5` : r.text_value}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Waiting on {evaluation.evaluator_name} to complete this evaluation.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
