import { HttpErrorResponse, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthStore } from '../services/auth.store';
import { ApiError } from '../services/api.client';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const auth = inject(AuthStore);
  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && !req.url.includes('/auth/')) {
        auth.logout();
        void router.navigate(['/auth/login']);
      }
      const code = (err.error as { error?: { code: string; message: string } })?.error?.code ?? 'unknown';
      const message = (err.error as { error?: { message: string } })?.error?.message ?? err.message;
      return throwError(() => new ApiError(code, message));
    }),
  );
};
