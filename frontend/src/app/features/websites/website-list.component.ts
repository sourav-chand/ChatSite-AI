import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { interval, switchMap, takeWhile } from 'rxjs';

import { WebsiteService } from '@core/services/domain.services';
import { Website } from '@app/models/domain';

@Component({
  selector: 'app-website-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-semibold">Websites</h1>
    </header>

    <form [formGroup]="form" (ngSubmit)="add()" class="flex gap-2 mb-6">
      <input formControlName="url" placeholder="https://example.com"
             class="flex-1 rounded border border-slate-300 px-3 py-2" />
      <input formControlName="name" placeholder="Display name"
             class="w-48 rounded border border-slate-300 px-3 py-2" />
      <button [disabled]="form.invalid"
              class="rounded bg-brand-600 text-white px-4 py-2 disabled:opacity-50">
        Add & crawl
      </button>
    </form>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      @for (site of sites(); track site.id) {
        <article class="rounded-xl bg-white border border-slate-200 p-5">
          <header class="flex items-start justify-between">
            <div>
              <h3 class="font-medium">{{ site.name }}</h3>
              <a [href]="site.url" target="_blank" class="text-xs text-slate-500 hover:underline">
                {{ site.url }}
              </a>
            </div>
            <span class="rounded-full px-2 py-0.5 text-xs"
                  [class.bg-emerald-100]="site.crawl_status === 'done'"
                  [class.bg-amber-100]="site.crawl_status === 'running'"
                  [class.bg-rose-100]="site.crawl_status === 'failed'"
                  [class.bg-slate-100]="site.crawl_status === 'idle' || site.crawl_status === 'paused'">
              {{ site.crawl_status }}
            </span>
          </header>
          <dl class="mt-3 text-sm text-slate-600 grid grid-cols-2 gap-1">
            <dt>Pages</dt><dd>{{ site.pages_count }}</dd>
            <dt>Chunks</dt><dd>{{ site.chunks_count }}</dd>
          </dl>
          <footer class="mt-3 flex gap-2 text-sm">
            <a [routerLink]="['/chatbots']" [queryParams]="{ website_id: site.id }"
               class="rounded bg-slate-100 px-2 py-1 hover:bg-slate-200">Build chatbot</a>
            <button (click)="recrawl(site.id)" class="rounded bg-slate-100 px-2 py-1 hover:bg-slate-200">Re-crawl</button>
            <button (click)="remove(site.id)" class="rounded text-rose-600 px-2 py-1 hover:bg-rose-50">Delete</button>
          </footer>
        </article>
      }
    </div>
  `,
})
export class WebsiteListComponent {
  private readonly fb = inject(FormBuilder);
  private readonly svc = inject(WebsiteService);

  readonly sites = signal<Website[]>([]);

  form = this.fb.nonNullable.group({
    url: ['', [Validators.required, Validators.pattern(/^https?:\/\//)]],
    name: ['', [Validators.required, Validators.minLength(2)]],
  });

  constructor() {
    void this.refresh();
    interval(5000)
      .pipe(
        switchMap(() => this.svc.list()),
        takeWhile(() => true, false),
      )
      .subscribe({
        next: (s) => this.sites.set(s),
        error: () => undefined,
      });
  }

  async add(): Promise<void> {
    if (this.form.invalid) return;
    await this.svc.create(this.form.getRawValue());
    this.form.reset();
    await this.refresh();
  }

  async refresh(): Promise<void> {
    this.sites.set(await this.svc.list());
  }

  async recrawl(id: string): Promise<void> {
    await this.svc.startCrawl(id, true);
    await this.refresh();
  }

  async remove(id: string): Promise<void> {
    await this.svc.delete(id);
    await this.refresh();
  }
}
