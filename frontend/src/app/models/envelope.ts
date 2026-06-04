/**
 * Typed API envelope. All backend responses use this shape.
 */
export interface ApiEnvelope<T> {
  data: T | null;
  meta?: Record<string, unknown>;
  error: { code: string; message: string; details?: Record<string, unknown> } | null;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface Paginated<T> {
  data: T[];
  meta: PageMeta;
}
