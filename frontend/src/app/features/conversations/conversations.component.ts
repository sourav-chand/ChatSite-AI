import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { ChatbotService, ConversationService } from '@core/services/domain.services';
import { Chatbot, Conversation, Message } from '@app/models/domain';

@Component({
  selector: 'app-conversations',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-semibold">Conversations</h1>
      <select [value]="selectedBotId()" (change)="onSelectBot($any($event.target).value)"
              class="rounded border border-slate-300 px-3 py-2 text-sm">
        @for (b of bots(); track b.id) {
          <option [value]="b.id">{{ b.name }}</option>
        }
      </select>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 h-[70vh]">
      <ul class="rounded-xl border border-slate-200 bg-white divide-y divide-slate-200 overflow-y-auto">
        @for (c of conversations(); track c.id) {
          <li>
            <button (click)="select(c)"
                    class="w-full text-left p-3 hover:bg-slate-50"
                    [class.bg-brand-50]="active()?.id === c.id">
              <div class="text-sm font-medium">{{ c.session_id.slice(0, 8) }}…</div>
              <div class="text-xs text-slate-500">{{ c.message_count }} msgs · {{ c.started_at | date: 'short' }}</div>
            </button>
          </li>
        }
      </ul>

      <div class="md:col-span-2 rounded-xl border border-slate-200 bg-white p-4 overflow-y-auto">
        @if (active(); as a) {
          <h2 class="text-sm font-medium mb-3">Session {{ a.session_id }}</h2>
          <div class="space-y-2">
            @for (m of messages(); track m.id) {
              <div [class.text-right]="m.role === 'user'">
                <div class="inline-block max-w-[80%] rounded px-3 py-2 text-sm"
                     [class.bg-brand-600]="m.role === 'user'"
                     [class.text-white]="m.role === 'user'"
                     [class.bg-slate-100]="m.role === 'assistant'">
                  {{ m.content }}
                </div>
              </div>
            }
          </div>
        } @else {
          <p class="text-sm text-slate-500">Select a conversation to read.</p>
        }
      </div>
    </div>
  `,
  imports: [],
})
export class ConversationsComponent {
  private readonly botSvc = inject(ChatbotService);
  private readonly convSvc = inject(ConversationService);

  readonly bots = signal<Chatbot[]>([]);
  readonly conversations = signal<Conversation[]>([]);
  readonly active = signal<Conversation | null>(null);
  readonly messages = signal<Message[]>([]);
  readonly selectedBotId = signal<string>('');

  constructor() {
    void this.init();
  }

  private async init(): Promise<void> {
    const b = await this.botSvc.list();
    this.bots.set(b);
    if (b[0]) this.selectedBotId.set(b[0].id);
    await this.refresh();
  }

  onSelectBot(id: string): void {
    this.selectedBotId.set(id);
    void this.refresh();
  }

  private async refresh(): Promise<void> {
    if (!this.selectedBotId()) return;
    const page = await this.convSvc.list(this.selectedBotId(), 1, 50);
    this.conversations.set(page.data);
  }

  async select(c: Conversation): Promise<void> {
    this.active.set(c);
    this.messages.set(await this.convSvc.messages(c.id));
  }
}
