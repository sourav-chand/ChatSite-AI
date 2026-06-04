import { computed, Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class LoadingStore {
  private readonly count = signal(0);
  readonly isLoading = computed(() => this.count() > 0);

  begin(): void {
    this.count.update((n) => n + 1);
  }

  end(): void {
    this.count.update((n) => Math.max(0, n - 1));
  }
}
