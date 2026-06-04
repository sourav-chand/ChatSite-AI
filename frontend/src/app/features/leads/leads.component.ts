import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { ChatbotService, LeadService } from '@core/services/domain.services';
import { Chatbot, Lead } from '@app/models/domain';

@Component({
  selector: 'app-leads',
  standalone: true,
  imports: [DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-semibold">Leads</h1>
      <div class="flex gap-2 items-center">
        <select [value]="selectedBotId()" (change)="onSelectBot($any($event.target).value)"
                class="rounded border border-slate-300 px-3 py-2 text-sm">
          @for (b of bots(); track b.id) {
            <option [value]="b.id">{{ b.name }}</option>
          }
        </select>
        <a [href]="exportUrl()" class="rounded bg-brand-600 text-white px-3 py-2 text-sm">Export CSV</a>
      </div>
    </header>

    <div class="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>
            <th class="p-3">Email</th>
            <th class="p-3">Name</th>
            <th class="p-3">Phone</th>
            <th class="p-3">Company</th>
            <th class="p-3">Captured</th>
            <th class="p-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-200">
          @for (l of leads(); track l.id) {
            <tr>
              <td class="p-3">{{ l.email }}</td>
              <td class="p-3">{{ l.name }}</td>
              <td class="p-3">{{ l.phone }}</td>
              <td class="p-3">{{ l.company }}</td>
              <td class="p-3 text-slate-500">{{ l.captured_at | date: 'short' }}</td>
              <td class="p-3 text-right">
                <button (click)="remove(l.id)" class="text-rose-600 text-xs">Delete</button>
              </td>
            </tr>
          } @empty {
            <tr><td colspan="6" class="p-6 text-center text-slate-500">No leads yet.</td></tr>
          }
        </tbody>
      </table>
    </div>
  `,
})
export class LeadsComponent {
  private readonly botSvc = inject(ChatbotService);
  private readonly svc = inject(LeadService);

  readonly bots = signal<Chatbot[]>([]);
  readonly leads = signal<Lead[]>([]);
  readonly selectedBotId = signal<string>('');

  exportUrl = () =>
    this.selectedBotId() ? this.svc.exportCsvUrl(this.selectedBotId()) : '#';

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
    const page = await this.svc.list(this.selectedBotId(), 1, 100);
    this.leads.set(page.data);
  }

  async remove(id: string): Promise<void> {
    await this.svc.delete(id);
    await this.refresh();
  }
}
