# ChatSite AI — System Architecture

## 1. High-Level Overview

ChatSite AI is a multi-tenant SaaS that turns any business website into an AI
chatbot knowledge base. Tenants (workspaces) own one or more websites, each of
which is crawled, chunked, embedded, and indexed into a workspace-scoped Qdrant
collection. A drop-in JavaScript widget exposes a streaming chat UI to end
visitors, with lead capture and analytics baked in.

```
                                ┌─────────────────────────────────────┐
                                │           Customer Website          │
                                │  <script src="cdn.chatsite.ai/...>  │
                                └───────────────┬─────────────────────┘
                                                │ SSE
                                                ▼
┌─────────────┐  HTTPS    ┌────────────────────────┐    async     ┌──────────────┐
│  Angular    │◀─────────▶│  Nginx (TLS, static)   │─────────────▶│  FastAPI     │
│  Frontend   │  /api/v1  │  Reverse Proxy         │              │  API (uvicorn)│
└─────────────┘           └────────────────────────┘              └──────┬───────┘
                                                                         │
                                          ┌──────────────────────────────┼──────────────────────────────┐
                                          │                              │                              │
                                          ▼                              ▼                              ▼
                                  ┌──────────────┐              ┌──────────────┐              ┌──────────────┐
                                  │ PostgreSQL 17│              │   Qdrant     │              │    Redis     │
                                  │  (tenants)   │              │  (vectors)   │              │ cache/broker │
                                  └──────────────┘              └──────────────┘              └──────┬───────┘
                                                                                                     │
                                                                       ┌─────────────────────────────┘
                                                                       ▼
                                                               ┌──────────────┐
                                                               │ Celery Worker│
                                                               │ + Beat (rollup)
                                                               └──────┬───────┘
                                                                      │
                                                                      ▼
                                                              ┌──────────────┐
                                                              │  OpenAI API  │
                                                              │ text-emb-3-sm│
                                                              │  gpt-4o      │
                                                              └──────────────┘
```

## 2. Tenant Isolation

| Layer      | Isolation strategy                                                |
|------------|--------------------------------------------------------------------|
| PostgreSQL | Every domain table carries `workspace_id` FK + RLS policy          |
| Qdrant     | One collection per workspace: `ws_{workspace_id}_vectors`          |
| Redis      | Key namespace `ws:{workspace_id}:{key}`                            |
| Files/CDN  | Workspace-scoped prefixes for any uploaded assets                  |

The `WorkspaceMiddleware` reads the JWT, resolves the active workspace, and
injects it into `request.state.workspace`. Repository classes receive the
workspace id as a mandatory argument and apply it as a filter on every query.

## 3. Data Flow — Indexing

```
URL ──▶ CrawlService ──▶ Robots/Sitemap check ──▶ Async httpx fetch
                                                       │
                                                       ▼
                                              BeautifulSoup extract
                                                       │
                                                       ▼
                                              Normalize + SHA-256 dedup
                                                       │
                                                       ▼
                                              ChunkingService
                                            (recursive|semantic|fixed)
                                                       │
                                                       ▼
                                              EmbeddingService
                                              (batches of 100)
                                                       │
                                                       ▼
                                            Qdrant upsert (per chunk)
                                                       │
                                                       ▼
                                            PostgreSQL metadata persist
```

## 4. Data Flow — Visitor Query

```
Visitor message ──▶ Prompt injection filter ──▶ Query rewrite (optional)
                                                       │
                                                       ▼
                                       Embed query (text-embedding-3-small)
                                                       │
                                                       ▼
                                  Qdrant cosine search (top_k=8, thr=0.72)
                                                       │
                                                       ▼
                                  Cross-encoder rerank (ms-marco) → top 4
                                                       │
                                                       ▼
                                       Context compress (>2000 tok)
                                                       │
                                                       ▼
                                       Prompt assembly + history (6 turns)
                                                       │
                                                       ▼
                                  gpt-4o (stream=true) ◀── LLMGateway
                                                       │
                                                       ▼
                                  SSE tokens + sources + confidence
```

## 5. Layered Architecture (Backend)

```
api/v1/*        ── thin FastAPI routers, validate input, return envelopes
   │
   ▼
services/*      ── business logic only, depends on repositories + clients
   │
   ▼
repositories/*  ── SQLAlchemy queries, workspace-scoped
   │
   ▼
models/*        ── ORM models
```

No DB calls in services. No business logic in repositories. No SQL in routers.

## 6. Layered Architecture (Frontend)

```
features/*      ── route-level pages (lazy)
   │
   ▼
shared/*        ── reusable components, pipes, directives
   │
   ▼
core/services   ── HTTP clients, signal stores, cross-cutting state
core/guards     ── AuthGuard, RoleGuard, WorkspaceGuard
core/interceptors ── auth header, error envelope, loading
```

State management is built on **Angular Signals**. RxJS is used only for HTTP
and event streams (e.g., crawl status polling).

## 7. Background Jobs

| Task                              | Trigger                  | Notes                          |
|-----------------------------------|--------------------------|--------------------------------|
| `crawl_website_task`              | API / schedule           | Orchestrator, dispatches pages |
| `crawl_page_task`                 | Celery (chord)           | One page, retry=3, exp backoff |
| `embed_chunks_task`               | After crawl completes    | 100 chunks / OpenAI batch      |
| `reindex_website_task`            | API                      | Drops vectors, re-crawls       |
| `analytics_daily_rollup_task`     | Celery beat, 00:05 UTC   | Aggregates analytics table     |
| `scheduled_crawl_task`            | Beat, per-workspace cron | Driven by `websites.crawl_config` |

## 8. Streaming Chat

`/api/v1/chat/stream` returns `text/event-stream` chunks. The widget uses
`fetch()` + `ReadableStream` for chunked decoding, and pushes each token
into the Shadow DOM message bubble. Sources and confidence are emitted as
named SSE events after the final token.

## 9. Observability

- `structlog` JSON logs on every request and Celery task
- LLM call latency + token usage persisted on every `messages` row
- Failed crawl pages persist `error_message` for support visibility
- `audit_logs` captures every write operation with before/after state

## 10. Scaling

- Stateless FastAPI workers behind Nginx → horizontal scale
- Celery workers scale independently
- Qdrant collection-per-workspace allows shard routing by workspace id
- Read replicas for PostgreSQL can be added by routing analytics queries to
  the replica via SQLAlchemy `bind` keys
