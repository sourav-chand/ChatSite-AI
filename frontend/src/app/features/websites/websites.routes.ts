import { Routes } from '@angular/router';

export const WEBSITES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./website-list.component').then((m) => m.WebsiteListComponent),
  },
];
