import { useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export interface QuestionDraft {
  text: string;
  type: 'rating' | 'text';
}

export interface CycleFormValues {
  name: string;
  start_date: string;
  end_date: string;
  questions: QuestionDraft[];
}

interface CycleFormProps {
  initialValues?: CycleFormValues;
  onSubmit: (values: CycleFormValues) => void;
  submitLabel: string;
  submittingLabel: string;
  submitting: boolean;
  error: string | null;
}

export function CycleForm({
  initialValues,
  onSubmit,
  submitLabel,
  submittingLabel,
  submitting,
  error,
}: CycleFormProps) {
  const [name, setName] = useState(initialValues?.name ?? '');
  const [startDate, setStartDate] = useState(initialValues?.start_date ?? '');
  const [endDate, setEndDate] = useState(initialValues?.end_date ?? '');
  const [questions, setQuestions] = useState<QuestionDraft[]>(
    initialValues?.questions ?? [{ text: '', type: 'rating' }]
  );

  function updateQuestion(index: number, patch: Partial<QuestionDraft>) {
    setQuestions((qs) => qs.map((q, i) => (i === index ? { ...q, ...patch } : q)));
  }

  function addQuestion() {
    setQuestions((qs) => [...qs, { text: '', type: 'rating' }]);
  }

  function removeQuestion(index: number) {
    setQuestions((qs) => qs.filter((_, i) => i !== index));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({ name, start_date: startDate, end_date: endDate, questions });
  }

  return (
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
        {submitting ? submittingLabel : submitLabel}
      </Button>
    </form>
  );
}
