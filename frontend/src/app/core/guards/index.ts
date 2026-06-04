import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';

import { AuthStore } from '../services/auth.store';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthStore);
  const router = inject(Router);
  if (auth.isAuthenticated()) return true;
  void router.navigate(['/auth/login']);
  return false;
};

export const workspaceGuard: CanActivateFn = () => {
  const auth = inject(AuthStore);
  const router = inject(Router);
  if (auth.workspace()) return true;
  void router.navigate(['/auth/login']);
  return false;
};

export const roleGuard =
  (allowed: string[]): CanActivateFn =>
  () => {
    const auth = inject(AuthStore);
    const router = inject(Router);
    const role = auth.workspace()?.plan ?? 'MEMBER';
    if (allowed.includes(role)) return true;
    void router.navigate(['/dashboard']);
    return false;
  };
