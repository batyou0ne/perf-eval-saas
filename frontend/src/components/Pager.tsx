import { Button } from '@/components/ui/button';

interface PagerProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

/** Prev/next control, hidden entirely when everything fits on one page. */
export function Pager({ page, totalPages, onPageChange }: PagerProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-3">
      <Button variant="outline" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        Previous
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {page} of {totalPages}
      </span>
      <Button variant="outline" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
        Next
      </Button>
    </div>
  );
}
