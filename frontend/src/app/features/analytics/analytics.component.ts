import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NgApexchartsModule } from 'ng-apexcharts';
import type { ApexOptions } from 'apexcharts';

import { AnalyticsService, ChatbotService } from '@core/services/domain.services';
import { Chatbot } from '@app/models/domain';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [NgApexchartsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-semibold">Analytics</h1>
      <select [value]="selectedBotId()" (change)="onSelect($any($event.target).value)"
              class="rounded border border-slate-300 px-3 py-2 text-sm">
        <option value="">All chatbots</option>
        @for (b of bots(); track b.id) {
          <option [value]="b.id">{{ b.name }}</option>
        }
      </select>
    </header>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      @for (m of cards(); track m.label) {
        <div class="rounded-xl bg-white border border-slate-200 p-4">
          <div class="text-xs text-slate-500">{{ m.label }}</div>
          <div class="text-2xl font-semibold mt-1">{{ m.value }}</div>
        </div>
      }
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="rounded-xl bg-white p-5 border border-slate-200">
        <h3 class="text-sm font-medium mb-2">Top pages</h3>
        <apx-chart [series]="pagesOptions.series!" [chart]="pagesOptions.chart!"
                   [xaxis]="pagesOptions.xaxis!" [plotOptions]="pagesOptions.plotOptions!" />
      </div>
      <div class="rounded-xl bg-white p-5 border border-slate-200">
        <h3 class="text-sm font-medium mb-2">Avg. session duration</h3>
        <apx-chart [series]="areaOptions.series!" [chart]="areaOptions.chart!"
                   [xaxis]="areaOptions.xaxis!" [stroke]="areaOptions.stroke!"
                   [fill]="areaOptions.fill!" />
      </div>
    </div>
  `,
})
export class AnalyticsComponent {
  private readonly analyticsSvc = inject(AnalyticsService);
  private readonly botSvc = inject(ChatbotService);

  readonly bots = signal<Chatbot[]>([]);
  readonly selectedBotId = signal<string>('');
  readonly cards = signal<{ label: string; value: string }[]>([]);

  readonly pagesOptions: ApexOptions = {
    chart: { type: 'bar', height: 280, toolbar: { show: false } },
    series: [{ name: 'Conversations', data: [12, 9, 7, 5, 4] }],
    xaxis: { categories: ['/', '/pricing', '/docs', '/blog', '/about'] },
    plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
  };

  readonly areaOptions: ApexOptions = {
    chart: { type: 'area', height: 280, toolbar: { show: false } },
    series: [{ name: 'Seconds', data: [120, 132, 101, 134, 90, 230, 210] }],
    xaxis: { categories: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] },
    stroke: { curve: 'smooth' },
    fill: { opacity: 0.3 },
  };

  constructor() {
    void this.init();
  }

  private async init(): Promise<void> {
    this.bots.set(await this.botSvc.list());
    await this.refresh();
  }

  onSelect(id: string): void {
    this.selectedBotId.set(id);
    void this.refresh();
  }

  private async refresh(): Promise<void> {
    const s = await this.analyticsSvc.summary(this.selectedBotId() || null, '30d');
    this.cards.set([
      { label: 'Unique visitors', value: String(s.unique_visitors) },
      { label: 'Conversations', value: String(s.total_conversations) },
      { label: 'Leads', value: String(s.leads_generated) },
      { label: 'Conversion', value: `${s.conversion_rate}%` },
      { label: 'Messages', value: String(s.total_messages) },
      { label: 'Avg latency', value: `${s.avg_response_latency_ms} ms` },
      { label: 'Tokens used', value: String(s.token_usage_total) },
      { label: 'Cost', value: `$${s.estimated_cost_usd}` },
    ]);
  }
}
