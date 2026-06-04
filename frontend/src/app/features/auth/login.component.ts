import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthStore } from '@core/services/auth.store';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4">
      <h2 class="text-xl font-semibold">Sign in</h2>
      <label class="block text-sm">
        <span class="text-slate-700">Email</span>
        <input type="email" formControlName="email" autocomplete="email"
               class="mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:border-brand-500 focus:ring focus:ring-brand-200" />
      </label>
      <label class="block text-sm">
        <span class="text-slate-700">Password</span>
        <input type="password" formControlName="password" autocomplete="current-password"
               class="mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:border-brand-500 focus:ring focus:ring-brand-200" />
      </label>
      @if (error()) {
        <p class="text-sm text-red-600">{{ error() }}</p>
      }
      <button type="submit" [disabled]="form.invalid || loading()"
              class="w-full rounded bg-brand-600 hover:bg-brand-700 text-white py-2 font-medium disabled:opacity-50">
        {{ loading() ? 'Signing in…' : 'Sign in' }}
      </button>
      <div class="flex items-center justify-between text-sm">
        <a routerLink="/auth/forgot-password" class="text-brand-600 hover:underline">Forgot password?</a>
        <a routerLink="/auth/register" class="text-brand-600 hover:underline">Create account</a>
      </div>
    </form>
  `,
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  async submit(): Promise<void> {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.error.set(null);
    try {
      const { email, password } = this.form.getRawValue();
      await this.auth.login(email, password);
      await this.router.navigateByUrl('/dashboard');
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : 'Login failed');
    } finally {
      this.loading.set(false);
    }
  }
}
