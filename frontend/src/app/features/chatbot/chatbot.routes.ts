import { Routes } from '@angular/router';

export const CHATBOT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./chatbot-builder.component').then((m) => m.ChatbotBuilderComponent),
  },
];
