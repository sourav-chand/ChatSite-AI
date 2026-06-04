import { HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize } from 'rxjs';

import { LoadingStore } from '../services/loading.store';

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loading = inject(LoadingStore);
  loading.begin();
  return next(req).pipe(finalize(() => loading.end()));
};
