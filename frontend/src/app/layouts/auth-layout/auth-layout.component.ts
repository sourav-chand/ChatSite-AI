import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-auth-layout',
  standalone: true,
  imports: [RouterOutlet],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-brand-50 p-4">
      <div class="w-full max-w-md rounded-2xl bg-white shadow-xl border border-slate-200 p-8">
        <div class="text-center mb-6">
          <h1 class="text-2xl font-semibold tracking-tight">ChatSite AI</h1>
          <p class="text-sm text-slate-500 mt-1">Build a chatbot trained on your website</p>
        </div>
        <router-outlet />
      </div>
    </div>
  `,
})
export class AuthLayoutComponent {}
