# Database ER Diagram (textual)

## Tables & Cardinality

```
users (1) ───< (N) workspaces
                  │
                  ├──< (N) workspace_members >─── (1) users
                  ├──< (N) websites
                  ├──< (N) chatbots ──< (N) conversations
                  ├──< (N) leads
                  ├──< (N) analytics
                  ├──< (N) analytics_daily
                  ├──< (N) subscriptions
                  ├──< (N) api_keys
                  └──< (N) audit_logs

websites (1) ───< (N) crawled_pages
websites (1) ───< (N) chunks
crawled_pages (1) ───< (N) chunks
chatbots (1) ───< (N) conversations
chatbots (1) ───< (N) leads
conversations (1) ───< (N) messages
conversations (1) ──< (1) leads (nullable)
```

## Indexes

- `users.email` UNIQUE
- `workspaces.subdomain` UNIQUE
- `chatbots.slug` UNIQUE
- `analytics_daily` composite (workspace_id, chatbot_id, date)
- `chunks(workspace_id, website_id, page_id)` B-tree
- `conversations(chatbot_id, started_at DESC)` for chat history queries
- `analytics(workspace_id, chatbot_id, event_type, created_at DESC)` for event drill-down

## RLS Policy Skeleton

```sql
ALTER TABLE websites       ENABLE ROW LEVEL SECURITY;
CREATE POLICY ws_isolation_websites ON websites
  USING (workspace_id = current_setting('app.current_workspace')::uuid);

ALTER TABLE chunks         ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads          ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics      ENABLE ROW LEVEL SECURITY;
-- (repeat per workspace-scoped table)
```

`WorkspaceMiddleware` issues `SELECT set_config('app.current_workspace', :ws, true)`
on every request before any query runs.
