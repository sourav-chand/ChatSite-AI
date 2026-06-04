import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { ApiClient } from '@core/services/api.client';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4">
      <h2 class="text-xl font-semibold">Choose a new password</h2>
      <input type="password" formControlName="new_password" placeholder="New password"
             class="w-full rounded border border-slate-300 px-3 py-2" />
      @if (message()) { <p class="text-sm text-emerald-600">{{ message() }}</p> }
      @if (error()) { <p class="text-sm text-red-600">{{ error() }}</p> }
      <button class="w-full rounded bg-brand-600 text-white py-2">Reset password</button>
    </form>
  `,
})
export class ResetPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ApiClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly message = signal<string | null>(null);
  readonly error = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    new_password: ['', [Validators.required, Validators.minLength(8)]],
  });

  async submit(): Promise<void> {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (!token) {
      this.error.set('Missing reset token');
      return;
    }
    try {
      await this.api
        .post('/auth/reset-password', { token, ...this.form.getRawValue() })
        .toPromise();
      this.message.set('Password updated. You can now sign in.');
      setTimeout(() => void this.router.navigateByUrl('/auth/login'), 1500);
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : 'Reset failed');
    }
  }
}
