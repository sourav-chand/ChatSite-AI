import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { ApiClient } from '@core/services/api.client';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="text-center space-y-3">
      <h2 class="text-xl font-semibold">Verifying your email…</h2>
      @if (state() === 'ok') {
        <p class="text-emerald-600">Email verified. Redirecting…</p>
      }
      @if (state() === 'error') {
        <p class="text-red-600">Invalid or expired token.</p>
      }
    </div>
  `,
})
export class VerifyEmailComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(ApiClient);

  readonly state = signal<'pending' | 'ok' | 'error'>('pending');

  constructor() {
    void this.run();
  }

  private async run(): Promise<void> {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (!token) {
      this.state.set('error');
      return;
    }
    try {
      await this.api.post('/auth/verify-email', { token }).toPromise();
      this.state.set('ok');
      setTimeout(() => void this.router.navigateByUrl('/auth/login'), 1500);
    } catch {
      this.state.set('error');
    }
  }
}
