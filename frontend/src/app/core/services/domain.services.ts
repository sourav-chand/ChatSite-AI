import { Injectable, inject } from '@angular/core';

import { ApiClient } from './api.client';
import { Chatbot, ChatResponse, ChatSource, Conversation, Lead, Message, Website } from '@app/models/domain';
import { Paginated } from '@app/models/envelope';

@Injectable({ providedIn: 'root' })
export class WebsiteService {
  private readonly api = inject(ApiClient);

  list(): Promise<Website[]> {
    return firstValue(this.api.get<Website[]>('/websites'));
  }

  get(id: string): Promise<Website> {
    return firstValue(this.api.get<Website>(`/websites/${id}`));
  }

  create(payload: { url: string; name: string; crawl_config?: Record<string, unknown> }): Promise<{ id: string }> {
    return firstValue(this.api.post('/websites', payload));
  }

  update(id: string, payload: Partial<Website>): Promise<Website> {
    return firstValue(this.api.put(`/websites/${id}`, payload));
  }

  delete(id: string): Promise<void> {
    return firstValue(this.api.delete<void>(`/websites/${id}`));
  }

  startCrawl(websiteId: string, force = false): Promise<{ status: string }> {
    return firstValue(this.api.post('/crawl/start', { website_id: websiteId, force_recrawl: force }));
  }

  stopCrawl(websiteId: string): Promise<{ status: string }> {
    return firstValue(this.api.post('/crawl/stop', { website_id: websiteId }));
  }

  crawlStatus(websiteId: string): Promise<{
    website_id: string;
    status: string;
    pages_crawled: number;
    pages_failed: number;
    chunks_embedded: number;
    celery_state: string | null;
  }> {
    return firstValue(this.api.get(`/crawl/status/${websiteId}`));
  }
}

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private readonly api = inject(ApiClient);

  list(): Promise<Chatbot[]> {
    return firstValue(this.api.get<Chatbot[]>('/chatbots'));
  }

  get(id: string): Promise<Chatbot> {
    return firstValue(this.api.get<Chatbot>(`/chatbots/${id}`));
  }

  create(payload: { website_id: string; name: string; settings: Chatbot['settings'] }): Promise<{ id: string; slug: string }> {
    return firstValue(this.api.post('/chatbots', payload));
  }

  update(id: string, payload: Partial<Chatbot>): Promise<Chatbot> {
    return firstValue(this.api.put(`/chatbots/${id}`, payload));
  }

  delete(id: string): Promise<void> {
    return firstValue(this.api.delete<void>(`/chatbots/${id}`));
  }

  embedCode(id: string): Promise<{ chatbot_id: string; snippet: string }> {
    return firstValue(this.api.get(`/chatbots/${id}/embed-code`));
  }
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly api = inject(ApiClient);

  query(payload: { chatbot_id: string; session_id: string; message: string; history?: { role: string; content: string }[] }): Promise<ChatResponse> {
    return firstValue(this.api.post<ChatResponse>('/chat/query', payload));
  }

  stream(
    payload: { chatbot_id: string; session_id: string; message: string; history?: { role: string; content: string }[] },
    onMeta: (sources: ChatSource[], confidence: string) => void,
    onToken: (delta: string) => void,
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const token = (this.api as unknown as { http: { get<T>(): unknown } }).http;
      void token;
      const base = (this.api as unknown as { base: string }).base;
      const body = JSON.stringify(payload);
      fetch(`${base}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      })
        .then(async (res) => {
          if (!res.body) throw new Error('No stream');
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split('\n\n');
            buffer = events.pop() ?? '';
            for (const ev of events) {
              const line = ev.trim();
              if (!line.startsWith('data:')) continue;
              const data = JSON.parse(line.slice(5)) as
                | { type: 'meta'; sources: ChatSource[]; confidence: string }
                | { type: 'token'; delta: string }
                | { type: 'done' }
                | { type: 'error'; message: string };
              if (data.type === 'meta') onMeta(data.sources, data.confidence);
              if (data.type === 'token') onToken(data.delta);
              if (data.type === 'done') resolve();
              if (data.type === 'error') reject(new Error(data.message));
            }
          }
          resolve();
        })
        .catch(reject);
    });
  }
}

@Injectable({ providedIn: 'root' })
export class ConversationService {
  private readonly api = inject(ApiClient);

  list(chatbotId: string, page = 1, pageSize = 20): Promise<Paginated<Conversation>> {
    return firstValue(this.api.getPaginated<Conversation>(`/conversations?chatbot_id=${chatbotId}`, page, pageSize));
  }

  messages(conversationId: string): Promise<Message[]> {
    return firstValue(this.api.get<Message[]>(`/conversations/${conversationId}/messages`));
  }
}

@Injectable({ providedIn: 'root' })
export class LeadService {
  private readonly api = inject(ApiClient);

  list(chatbotId: string, page = 1, pageSize = 20): Promise<Paginated<Lead>> {
    return firstValue(this.api.getPaginated<Lead>(`/leads?chatbot_id=${chatbotId}`, page, pageSize));
  }

  delete(id: string): Promise<void> {
    return firstValue(this.api.delete<void>(`/leads/${id}`));
  }

  exportCsvUrl(chatbotId: string): string {
    return `${(this.api as unknown as { base: string }).base}/leads/export?chatbot_id=${chatbotId}&format=csv`;
  }
}

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly api = inject(ApiClient);

  summary(chatbotId: string | null, period = '30d'): Promise<{
    unique_visitors: number;
    total_conversations: number;
    total_messages: number;
    leads_generated: number;
    conversion_rate: number;
    avg_messages_per_conversation: number;
    avg_response_latency_ms: number;
    token_usage_total: number;
    estimated_cost_usd: number;
  }> {
    const params: Record<string, string> = { period };
    if (chatbotId) params['chatbot_id'] = chatbotId;
    return firstValue(this.api.get('/analytics/summary', params));
  }
}

function firstValue<T>(obs: import('rxjs').Observable<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    obs.subscribe({ next: resolve, error: reject });
  });
}
