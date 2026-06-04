import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { ApiClient } from '@core/services/api.client';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4">
      <h2 class="text-xl font-semibold">Reset password</h2>
      <p class="text-sm text-slate-500">We'll email you a reset link.</p>
      <input type="email" formControlName="email" placeholder="you@company.com"
             class="w-full rounded border border-slate-300 px-3 py-2" />
      @if (message()) { <p class="text-sm text-emerald-600">{{ message() }}</p> }
      <button class="w-full rounded bg-brand-600 text-white py-2">Send link</button>
    </form>
  `,
})
export class ForgotPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ApiClient);
  readonly message = signal<string | null>(null);

  form = this.fb.nonNullable.group({ email: ['', [Validators.required, Validators.email]] });

  async submit(): Promise<void> {
    if (this.form.invalid) return;
    await this.api.post('/auth/forgot-password', this.form.getRawValue()).toPromise();
    this.message.set('If that email exists, a reset link has been sent.');
  }
}
