/** Mirrors the backend's Page[T] envelope (app/schemas/pagination.py). */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const PAGE_SIZE = 20;

export function totalPages(data: Page<unknown>): number {
  return Math.max(1, Math.ceil(data.total / data.page_size));
}
