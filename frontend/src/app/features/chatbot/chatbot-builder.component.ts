import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { ChatbotService, WebsiteService } from '@core/services/domain.services';
import { Chatbot, Website } from '@app/models/domain';

@Component({
  selector: 'app-chatbot-builder',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-semibold">Chatbots</h1>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <section>
        <h2 class="text-sm font-medium mb-2">List</h2>
        <ul class="space-y-2">
          @for (bot of chatbots(); track bot.id) {
            <li>
              <button (click)="select(bot)"
                      class="w-full text-left rounded-lg border border-slate-200 p-3 hover:border-brand-500"
                      [class.border-brand-500]="selected()?.id === bot.id">
                <div class="font-medium">{{ bot.name }}</div>
                <div class="text-xs text-slate-500">slug: {{ bot.slug }}</div>
              </button>
            </li>
          }
        </ul>
      </section>

      <section>
        <h2 class="text-sm font-medium mb-2">Customize</h2>
        @if (selected(); as bot) {
          <form [formGroup]="form" (ngSubmit)="save()" class="space-y-3 rounded-xl border border-slate-200 p-4 bg-white">
            <label class="block text-sm">
              <span class="text-slate-700">Name</span>
              <input formControlName="name" class="mt-1 w-full rounded border border-slate-300 px-3 py-2" />
            </label>
            <label class="block text-sm">
              <span class="text-slate-700">Welcome message</span>
              <textarea formControlName="welcome_message" rows="2"
                        class="mt-1 w-full rounded border border-slate-300 px-3 py-2"></textarea>
            </label>
            <label class="block text-sm">
              <span class="text-slate-700">Primary color</span>
              <input type="color" formControlName="primary_color" class="ml-2 h-9 w-16" />
            </label>
            <label class="block text-sm">
              <span class="text-slate-700">Theme</span>
              <select formControlName="theme" class="mt-1 rounded border border-slate-300 px-3 py-2">
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto</option>
              </select>
            </label>
            <label class="block text-sm">
              <span class="text-slate-700">Position</span>
              <select formControlName="position" class="mt-1 rounded border border-slate-300 px-3 py-2">
                <option value="bottom-right">Bottom right</option>
                <option value="bottom-left">Bottom left</option>
              </select>
            </label>
            <label class="block text-sm">
              <span class="text-slate-700">Allowed domains (comma-separated)</span>
              <input formControlName="allowed_domains" class="mt-1 w-full rounded border border-slate-300 px-3 py-2" />
            </label>
            <div class="flex items-center gap-3 pt-2">
              <button class="rounded bg-brand-600 text-white px-4 py-2">Save</button>
              @if (embed(); as e) {
                <button type="button" (click)="copyEmbed()"
                        class="rounded bg-slate-100 px-3 py-2 text-sm">Copy embed code</button>
              }
            </div>
          </form>
        } @else {
          <p class="text-sm text-slate-500">Select a chatbot to customize.</p>
        }
      </section>
    </div>

    @if (embed(); as e) {
      <section class="mt-6">
        <h2 class="text-sm font-medium mb-2">Embed code</h2>
        <pre class="rounded bg-slate-900 text-slate-100 p-4 text-xs overflow-x-auto">{{ e.snippet }}</pre>
      </section>
    }
  `,
})
export class ChatbotBuilderComponent {
  private readonly fb = inject(FormBuilder);
  private readonly botSvc = inject(ChatbotService);
  private readonly webSvc = inject(WebsiteService);

  readonly chatbots = signal<Chatbot[]>([]);
  readonly selected = signal<Chatbot | null>(null);
  readonly embed = signal<{ chatbot_id: string; snippet: string } | null>(null);

  form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    welcome_message: [''],
    primary_color: ['#4F46E5'],
    theme: ['light'],
    position: ['bottom-right'],
    allowed_domains: [''],
  });

  constructor() {
    void this.refresh();
  }

  async refresh(): Promise<void> {
    this.chatbots.set(await this.botSvc.list());
  }

  select(bot: Chatbot): void {
    this.selected.set(bot);
    this.form.patchValue({
      name: bot.name,
      welcome_message: bot.settings.welcome_message,
      primary_color: bot.settings.primary_color,
      theme: bot.settings.theme,
      position: bot.settings.position,
      allowed_domains: bot.allowed_domains.join(', '),
    });
    void this.botSvc.embedCode(bot.id).then((e) => this.embed.set(e));
  }

  async save(): Promise<void> {
    const bot = this.selected();
    if (!bot) return;
    const v = this.form.getRawValue();
    await this.botSvc.update(bot.id, {
      name: v.name,
      settings: {
        ...bot.settings,
        welcome_message: v.welcome_message,
        primary_color: v.primary_color,
        theme: v.theme as 'light' | 'dark' | 'auto',
        position: v.position as 'bottom-right' | 'bottom-left',
      },
      allowed_domains: v.allowed_domains.split(',').map((s) => s.trim()).filter(Boolean),
    });
    await this.refresh();
  }

  async copyEmbed(): Promise<void> {
    const e = this.embed();
    if (e) await navigator.clipboard.writeText(e.snippet);
  }
}
