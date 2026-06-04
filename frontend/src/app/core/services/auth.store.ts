import { computed, Injectable, signal } from '@angular/core';

import { ApiClient, ApiError } from './api.client';
import { User, Workspace } from '@app/models/domain';

const ACCESS_KEY = 'cs.access';
const REFRESH_COOKIE = 'cs_refresh';
const WORKSPACE_KEY = 'cs.workspace';

interface AccessPayload {
  exp: number;
  sub: string;
  ws: string;
  role: string;
}

@Injectable({ providedIn: 'root' })
export class AuthStore {
  private readonly api = new ApiClient();

  readonly accessToken = signal<string | null>(localStorage.getItem(ACCESS_KEY));
  readonly user = signal<User | null>(null);
  readonly workspace = signal<Workspace | null>(
    JSON.parse(localStorage.getItem(WORKSPACE_KEY) ?? 'null'),
  );
  readonly isAuthenticated = computed(() => !!this.accessToken());

  async bootstrap(): Promise<void> {
    const token = this.accessToken();
    if (!token) return;
    if (this.isExpired(token)) {
      await this.silentRefresh();
      if (!this.accessToken()) return;
    }
    try {
      const me = await this.api.get<User>('/auth/me').toPromise();
      this.user.set(me ?? null);
    } catch {
      this.clear();
    }
  }

  async login(email: string, password: string): Promise<void> {
    const pair = await this.api
      .post<{ access_token: string; refresh_token: string; expires_in: number }>(
        '/auth/login',
        { email, password },
      )
      .toPromise();
    if (!pair) throw new ApiError('login_failed', 'No token returned');
    this.setAccess(pair.access_token, pair.expires_in);
    document.cookie = `${REFRESH_COOKIE}=${pair.refresh_token}; HttpOnly; Secure; SameSite=Strict; Path=/`;
  }

  async register(email: string, password: string, fullName: string): Promise<void> {
    await this.api.post('/auth/register', { email, password, full_name: fullName }).toPromise();
  }

  async logout(): Promise<void> {
    try {
      await this.api.post('/auth/logout', {}).toPromise();
    } finally {
      this.clear();
    }
  }

  setWorkspace(ws: Workspace): void {
    this.workspace.set(ws);
    localStorage.setItem(WORKSPACE_KEY, JSON.stringify(ws));
  }

  private setAccess(token: string, expiresIn: number): void {
    this.accessToken.set(token);
    localStorage.setItem(ACCESS_KEY, token);
    setTimeout(() => void this.silentRefresh(), (expiresIn - 60) * 1000);
  }

  private clear(): void {
    this.accessToken.set(null);
    this.user.set(null);
    this.workspace.set(null);
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(WORKSPACE_KEY);
    document.cookie = `${REFRESH_COOKIE}=; Max-Age=0; Path=/`;
  }

  private isExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1])) as AccessPayload;
      return payload.exp * 1000 < Date.now();
    } catch {
      return true;
    }
  }

  private async silentRefresh(): Promise<void> {
    try {
      await this.api.post('/auth/session/refresh', {}).toPromise();
    } catch {
      this.clear();
    }
  }
}
