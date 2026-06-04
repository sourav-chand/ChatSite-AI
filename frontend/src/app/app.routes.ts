import { Routes } from '@angular/router';
import { authGuard, roleGuard, workspaceGuard } from '@core/guards';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('@layouts/app-shell/app-shell.component').then((m) => m.AppShellComponent),
    canActivate: [authGuard, workspaceGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('@features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'websites',
        loadChildren: () =>
          import('@features/websites/websites.routes').then((m) => m.WEBSITES_ROUTES),
      },
      {
        path: 'chatbots',
        loadChildren: () =>
          import('@features/chatbot/chatbot.routes').then((m) => m.CHATBOT_ROUTES),
      },
      {
        path: 'analytics',
        loadComponent: () =>
          import('@features/analytics/analytics.component').then((m) => m.AnalyticsComponent),
      },
      {
        path: 'conversations',
        loadComponent: () =>
          import('@features/conversations/conversations.component').then(
            (m) => m.ConversationsComponent,
          ),
      },
      {
        path: 'leads',
        loadComponent: () =>
          import('@features/leads/leads.component').then((m) => m.LeadsComponent),
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('@features/settings/settings.component').then((m) => m.SettingsComponent),
        canActivate: [roleGuard(['OWNER', 'ADMIN'])],
      },
    ],
  },
  {
    path: 'auth',
    loadComponent: () =>
      import('@layouts/auth-layout/auth-layout.component').then((m) => m.AuthLayoutComponent),
    children: [
      {
        path: 'login',
        loadComponent: () =>
          import('@features/auth/login.component').then((m) => m.LoginComponent),
      },
      {
        path: 'register',
        loadComponent: () =>
          import('@features/auth/register.component').then((m) => m.RegisterComponent),
      },
      {
        path: 'forgot-password',
        loadComponent: () =>
          import('@features/auth/forgot-password.component').then(
            (m) => m.ForgotPasswordComponent,
          ),
      },
      {
        path: 'reset-password',
        loadComponent: () =>
          import('@features/auth/reset-password.component').then((m) => m.ResetPasswordComponent),
      },
      {
        path: 'verify-email',
        loadComponent: () =>
          import('@features/auth/verify-email.component').then((m) => m.VerifyEmailComponent),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
