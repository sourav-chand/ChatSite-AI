import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthStore } from '@core/services/auth.store';
import { LoadingStore } from '@core/services/loading.store';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex h-screen bg-slate-50 text-slate-900">
      <aside class="hidden md:flex md:w-60 flex-col bg-white border-r border-slate-200">
        <div class="px-5 py-4 border-b border-slate-200">
          <span class="text-lg font-semibold tracking-tight">ChatSite AI</span>
        </div>
        <nav class="flex-1 px-2 py-3 space-y-1 text-sm">
          <a routerLink="/dashboard" routerLinkActive="bg-brand-50 text-brand-700"
             class="flex items-center gap-2 rounded px-3 py-2 hover:bg-slate-100">
            <span class="material-icons text-base">dashboard</span> Dashboard
          </a>
          <a routerLink="/websites" routerLinkActive="bg-brand-50 text-brand-700"
             class="flex items-center gap-2 rounded px-3 py-2 hover:bg-slate-100">
            <span class="material-icons text-base">public</span> Websites
          </a>
          <a routerLink="/chatbots" routerLinkActive="bg-brand-50 text-brand-700"
             class="flex items-center gap-2 rounded px-3 py-2 hover:bg-slate-100">
            <span class="material-icons text-base">smart_toy</span> Chatbots
          </a>
          <a routerLink="/analytics" routerLinkActive="bg-brand-50 text-brand-700"
             class="flex items-center gap-2 rounded px-3 py-2 hover:bg-slate-100">
            <span class="material-icons text-base">insights</span> Analytics
          </a>
          <a routerLink="/conversations" routerLinkActive="bg-brand-50 text-brand-700"
             class="flex items-center gap-2 rounded px-3 py-2 hover:bg-slate-100">
            <span class="material-icons text-base">forum</span> Conversations
          </a>
          <a routerLink="/leads" routerLinkActive="bg-brand-50 text-brand-700"
             class="flex items-center gap-2 rounded px-3 py-2 hover:bg-slate-100">
            <span class="material-icons text-base">contacts</span> Leads
          </a>
          <a routerLink="/settings" routerLinkActive="bg-brand-50 text-brand-700"
             class="flex items-center gap-2 rounded px-3 py-2 hover:bg-slate-100">
            <span class="material-icons text-base">settings</span> Settings
          </a>
        </nav>
        <div class="p-3 border-t border-slate-200">
          <button (click)="logout()" class="w-full text-left text-sm px-3 py-2 rounded hover:bg-slate-100">
            Sign out
          </button>
        </div>
      </aside>
      <main class="flex-1 overflow-y-auto">
        <header class="h-14 flex items-center justify-end px-5 border-b border-slate-200 bg-white">
          <span class="text-sm text-slate-500">{{ workspaceName() }}</span>
        </header>
        @if (loading.isLoading()) {
          <div class="h-0.5 bg-brand-500 animate-pulse"></div>
        }
        <section class="p-6">
          <router-outlet />
        </section>
      </main>
    </div>
  `,
})
export class AppShellComponent {
  private readonly auth = inject(AuthStore);
  readonly loading = inject(LoadingStore);

  workspaceName = () => this.auth.workspace()?.name ?? '—';

  async logout(): Promise<void> {
    await this.auth.logout();
  }
}
