import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { environment } from '@env/environment';
import { ApiEnvelope, Paginated } from '@app/models/envelope';

@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  get<T>(path: string, params?: Record<string, string | number>): Observable<T> {
    return this.http
      .get<ApiEnvelope<T>>(`${this.base}${path}`, { params: this.toParams(params) })
      .pipe(map((r) => this.unwrap(r)));
  }

  post<T>(path: string, body: unknown, params?: Record<string, string | number>): Observable<T> {
    return this.http
      .post<ApiEnvelope<T>>(`${this.base}${path}`, body, { params: this.toParams(params) })
      .pipe(map((r) => this.unwrap(r)));
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http
      .put<ApiEnvelope<T>>(`${this.base}${path}`, body)
      .pipe(map((r) => this.unwrap(r)));
  }

  delete<T>(path: string): Observable<T> {
    return this.http
      .delete<ApiEnvelope<T>>(`${this.base}${path}`)
      .pipe(map((r) => this.unwrap(r)));
  }

  postPaginated<T>(path: string, body: unknown, page = 1, pageSize = 20): Observable<Paginated<T>> {
    return this.post<{ items: T[]; total: number }>(path, body, { page, page_size: pageSize }).pipe(
      map((r) => ({
        data: (r as { items: T[] }).items,
        meta: { page, page_size: pageSize, total: (r as { total: number }).total },
      })),
    );
  }

  getPaginated<T>(path: string, page = 1, pageSize = 20): Observable<Paginated<T>> {
    return this.get<{ items: T[]; total: number }>(path, { page, page_size: pageSize }).pipe(
      map((r) => ({
        data: (r as { items: T[] }).items,
        meta: { page, page_size: pageSize, total: (r as { total: number }).total },
      })),
    );
  }

  private unwrap<T>(r: ApiEnvelope<T>): T {
    if (r.error) {
      throw new ApiError(r.error.code, r.error.message, r.error.details);
    }
    return r.data as T;
  }

  private toParams(p?: Record<string, string | number>): HttpParams {
    let params = new HttpParams();
    if (p) {
      for (const [k, v] of Object.entries(p)) {
        if (v !== undefined && v !== null) params = params.set(k, String(v));
      }
    }
    return params;
  }
}

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
  }
}
