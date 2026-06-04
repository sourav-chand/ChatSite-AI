import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthStore } from '@core/services/auth.store';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4">
      <h2 class="text-xl font-semibold">Create your account</h2>
      <label class="block text-sm">
        <span class="text-slate-700">Full name</span>
        <input formControlName="full_name" autocomplete="name"
               class="mt-1 w-full rounded border border-slate-300 px-3 py-2" />
      </label>
      <label class="block text-sm">
        <span class="text-slate-700">Email</span>
        <input type="email" formControlName="email" autocomplete="email"
               class="mt-1 w-full rounded border border-slate-300 px-3 py-2" />
      </label>
      <label class="block text-sm">
        <span class="text-slate-700">Password</span>
        <input type="password" formControlName="password" autocomplete="new-password"
               class="mt-1 w-full rounded border border-slate-300 px-3 py-2" />
      </label>
      @if (message()) { <p class="text-sm text-emerald-600">{{ message() }}</p> }
      @if (error()) { <p class="text-sm text-red-600">{{ error() }}</p> }
      <button type="submit" [disabled]="form.invalid || loading()"
              class="w-full rounded bg-brand-600 text-white py-2 font-medium disabled:opacity-50">
        {{ loading() ? 'Creating…' : 'Create account' }}
      </button>
      <a routerLink="/auth/login" class="block text-center text-sm text-brand-600 hover:underline">
        Back to sign in
      </a>
    </form>
  `,
})
export class RegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthStore);

  readonly loading = signal(false);
  readonly message = signal<string | null>(null);
  readonly error = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    full_name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  async submit(): Promise<void> {
    if (this.form.invalid) return;
    this.loading.set(true);
    try {
      const v = this.form.getRawValue();
      await this.auth.register(v.email, v.password, v.full_name);
      this.message.set('Account created. Check your email to verify before logging in.');
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : 'Registration failed');
    } finally {
      this.loading.set(false);
    }
  }
}
