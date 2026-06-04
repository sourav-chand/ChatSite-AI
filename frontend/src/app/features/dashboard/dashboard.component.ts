import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { NgApexchartsModule } from 'ng-apexcharts';
import type { ApexOptions } from 'apexcharts';

import { AnalyticsService, ChatbotService, WebsiteService } from '@core/services/domain.services';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NgApexchartsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1 class="text-2xl font-semibold mb-6">Dashboard</h1>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      @for (m of metrics(); track m.label) {
        <div class="rounded-xl bg-white p-5 border border-slate-200">
          <div class="text-sm text-slate-500">{{ m.label }}</div>
          <div class="text-2xl font-semibold mt-1">{{ m.value }}</div>
        </div>
      }
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
      <div class="rounded-xl bg-white p-5 border border-slate-200">
        <h3 class="text-sm font-medium mb-2">Daily chat volume (30d)</h3>
        <apx-chart [series]="lineOptions.series!" [chart]="lineOptions.chart!"
                   [xaxis]="lineOptions.xaxis!" [stroke]="lineOptions.stroke!"
                   [colors]="lineOptions.colors!" />
      </div>
      <div class="rounded-xl bg-white p-5 border border-slate-200">
        <h3 class="text-sm font-medium mb-2">Leads generated (30d)</h3>
        <apx-chart [series]="barOptions.series!" [chart]="barOptions.chart!"
                   [xaxis]="barOptions.xaxis!" [plotOptions]="barOptions.plotOptions!" />
      </div>
    </div>
  `,
})
export class DashboardComponent {
  private readonly analytics = inject(AnalyticsService);
  private readonly websites = inject(WebsiteService);
  private readonly chatbots = inject(ChatbotService);

  readonly metrics = signal<{ label: string; value: string }[]>([]);

  readonly lineOptions: ApexOptions = {
    chart: { type: 'line', height: 240, toolbar: { show: false } },
    series: [{ name: 'Chats', data: Array.from({ length: 30 }, () => Math.floor(Math.random() * 80)) }],
    xaxis: { categories: Array.from({ length: 30 }, (_, i) => `D-${30 - i}`) },
    stroke: { curve: 'smooth', width: 2 },
    colors: ['#4F46E5'],
  };

  readonly barOptions: ApexOptions = {
    chart: { type: 'bar', height: 240, toolbar: { show: false } },
    series: [{ name: 'Leads', data: Array.from({ length: 30 }, () => Math.floor(Math.random() * 12)) }],
    xaxis: { categories: Array.from({ length: 30 }, (_, i) => `D-${30 - i}`) },
    plotOptions: { bar: { borderRadius: 4, columnWidth: '60%' } },
  };

  constructor() {
    void this.load();
  }

  private async load(): Promise<void> {
    const [summary, sites, bots] = await Promise.all([
      this.analytics.summary(null, '30d'),
      this.websites.list().catch(() => []),
      this.chatbots.list().catch(() => []),
    ]);
    this.metrics.set([
      { label: 'Total chats (30d)', value: String(summary.total_conversations) },
      { label: 'Total messages', value: String(summary.total_messages) },
      { label: 'Leads captured', value: String(summary.leads_generated) },
      { label: 'Unique visitors', value: String(summary.unique_visitors) },
      { label: 'Websites', value: String(sites.length) },
      { label: 'Chatbots', value: String(bots.length) },
      { label: 'Conversion rate', value: `${summary.conversion_rate}%` },
      { label: 'Estimated cost', value: `$${summary.estimated_cost_usd}` },
    ]);
  }
}
