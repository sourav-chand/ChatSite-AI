import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { ApiClient } from '@core/services/api.client';
import { AuthStore } from '@core/services/auth.store';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1 class="text-2xl font-semibold mb-6">Workspace settings</h1>

    @if (ws(); as w) {
      <form [formGroup]="form" (ngSubmit)="save()" class="space-y-4 max-w-md">
        <label class="block text-sm">
          <span class="text-slate-700">Workspace name</span>
          <input formControlName="name" class="mt-1 w-full rounded border border-slate-300 px-3 py-2" />
        </label>
        <label class="block text-sm">
          <span class="text-slate-700">Subdomain</span>
          <input formControlName="subdomain" class="mt-1 w-full rounded border border-slate-300 px-3 py-2" />
        </label>
        <label class="block text-sm">
          <span class="text-slate-700">Default AI model</span>
          <select formControlName="ai_model" class="mt-1 rounded border border-slate-300 px-3 py-2">
            <option value="gpt-4o">gpt-4o (OpenAI)</option>
            <option value="gemini-2.0-flash">gemini-2.0-flash (Google)</option>
          </select>
        </label>
        <button class="rounded bg-brand-600 text-white px-4 py-2">Save</button>
        @if (message()) { <p class="text-sm text-emerald-600">{{ message() }}</p> }
      </form>
    }
  `,
})
export class SettingsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ApiClient);
  private readonly auth = inject(AuthStore);

  readonly ws = this.auth.workspace;
  readonly message = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    name: [''],
    subdomain: [{ value: '', disabled: true }],
    ai_model: ['gpt-4o'],
  });

  constructor() {
    const w = this.ws();
    if (w) {
      this.form.patchValue({
        name: w.name,
        subdomain: w.subdomain,
        ai_model: (w.settings as { ai_model?: string })?.ai_model ?? 'gpt-4o',
      });
    }
  }

  async save(): Promise<void> {
    const w = this.ws();
    if (!w) return;
    const v = this.form.getRawValue();
    const updated = await this.api
      .put(`/workspaces/${w.id}`, { name: v.name, settings: { ai_model: v.ai_model } })
      .toPromise();
    this.auth.setWorkspace({ ...w, name: v.name, settings: { ...w.settings, ai_model: v.ai_model } });
    this.message.set('Saved');
  }
}
