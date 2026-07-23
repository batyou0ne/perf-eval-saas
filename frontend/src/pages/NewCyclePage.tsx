import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetchJson, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';

interface QuestionDraft {
  text: string;
  type: 'rating' | 'text';
}

export function NewCyclePage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [questions, setQuestions] = useState<QuestionDraft[]>([{ text: '', type: 'rating' }]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function updateQuestion(index: number, patch: Partial<QuestionDraft>) {
    setQuestions((qs) => qs.map((q, i) => (i === index ? { ...q, ...patch } : q)));
  }

  function addQuestion() {
    setQuestions((qs) => [...qs, { text: '', type: 'rating' }]);
  }

  function removeQuestion(index: number) {
    setQuestions((qs) => qs.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const cycle = await apiFetchJson<{ id: string }>('/api/v1/cycles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          start_date: startDate,
          end_date: endDate,
          questions: questions.map((q, i) => ({ text: q.text, type: q.type, order: i })),
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
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="cycle-name">Name</Label>
              <Input id="cycle-name" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="flex gap-4">
              <div className="flex flex-1 flex-col gap-2">
                <Label htmlFor="start-date">Start date</Label>
                <Input
                  id="start-date"
                  type="date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="flex flex-1 flex-col gap-2">
                <Label htmlFor="end-date">End date</Label>
                <Input id="end-date" type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <Label>Questions</Label>
              {questions.map((q, i) => (
                <div key={i} className="flex items-start gap-2">
                  <Input
                    placeholder="Question text"
                    required
                    value={q.text}
                    onChange={(e) => updateQuestion(i, { text: e.target.value })}
                  />
                  <select
                    className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm"
                    value={q.type}
                    onChange={(e) => updateQuestion(i, { type: e.target.value as 'rating' | 'text' })}
                  >
                    <option value="rating">Rating</option>
                    <option value="text">Text</option>
                  </select>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={questions.length === 1}
                    onClick={() => removeQuestion(i)}
                  >
                    Remove
                  </Button>
                </div>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={addQuestion} className="self-start">
                Add question
              </Button>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create cycle'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
