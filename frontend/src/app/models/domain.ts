export interface User {
  id: string;
  email: string;
  full_name: string;
  is_verified: boolean;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

export interface Workspace {
  id: string;
  owner_id: string;
  name: string;
  subdomain: string;
  plan: 'free' | 'starter' | 'pro' | 'enterprise';
  settings: Record<string, unknown>;
  created_at: string;
}

export type CrawlStatus = 'idle' | 'running' | 'paused' | 'done' | 'failed';

export interface Website {
  id: string;
  workspace_id: string;
  url: string;
  name: string;
  favicon_url: string | null;
  crawl_status: CrawlStatus;
  last_crawled_at: string | null;
  pages_count: number;
  chunks_count: number;
  crawl_config: Record<string, unknown>;
}

export interface Chatbot {
  id: string;
  workspace_id: string;
  website_id: string;
  name: string;
  slug: string;
  is_active: boolean;
  allowed_domains: string[];
  settings: {
    theme: 'light' | 'dark' | 'auto';
    position: 'bottom-left' | 'bottom-right';
    primary_color: string;
    welcome_message: string;
    suggested_questions: string[];
    lead_capture: {
      enabled: boolean;
      trigger: 'after_n_messages' | 'exit_intent' | 'before_first' | 'disabled';
      trigger_after: number;
      fields: { name: boolean; email: boolean; phone: boolean; company: boolean };
    };
    rag: {
      rewrite_query: boolean;
      multi_query: boolean;
      rerank: boolean;
      compress: boolean;
      model: string;
    };
  };
  created_at: string;
}

export interface ChatSource {
  url: string;
  title: string | null;
  score: number;
}

export interface ChatResponse {
  response: string;
  sources: ChatSource[];
  confidence: 'high' | 'medium' | 'low';
  suggested_questions: string[];
  model_used: string;
  latency_ms: number;
}

export interface Conversation {
  id: string;
  chatbot_id: string;
  session_id: string;
  started_at: string;
  ended_at: string | null;
  message_count: number;
  page_url: string | null;
  lead_id: string | null;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources: ChatSource[];
  model_used: string | null;
  latency_ms: number;
  confidence: string | null;
  created_at: string;
}

export interface Lead {
  id: string;
  workspace_id: string;
  chatbot_id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  company: string | null;
  source_page_url: string | null;
  captured_at: string;
}

export interface AnalyticsSummary {
  period: string;
  unique_visitors: number;
  total_conversations: number;
  total_messages: number;
  leads_generated: number;
  conversion_rate: number;
  avg_messages_per_conversation: number;
  avg_response_latency_ms: number;
  token_usage_total: number;
  estimated_cost_usd: number;
}
