# Qdrant Collection Schema

## Naming

```
ws_{workspace_id}_vectors
```

## Vector Config

- `size`: 1536 (text-embedding-3-small)
- `distance`: Cosine
- `on_disk_payload`: true

## Payload Indexes

| Field         | Type   | Notes                          |
|---------------|--------|--------------------------------|
| workspace_id  | uuid   | keyword                        |
| website_id    | uuid   | keyword                        |
| page_id       | uuid   | keyword                        |
| chunk_id      | uuid   | keyword                        |
| source_url    | text   | full-text optional             |
| created_at    | iso    | datetime                       |

## Point Schema

```json
{
  "id": "<chunk_uuid>",
  "vector": [/* 1536 floats */],
  "payload": {
    "workspace_id": "uuid",
    "website_id":   "uuid",
    "page_id":      "uuid",
    "chunk_id":     "uuid",
    "source_url":   "https://...",
    "title":        "string",
    "heading_context": "h1 > h2 string",
    "content":      "string (chunk text)",
    "token_count":  512,
    "chunk_index":  0,
    "created_at":   "2026-06-04T12:00:00Z"
  }
}
```

## Operations

- `create_collection(workspace_id)` — called lazily on first embed
- `upsert_chunks(workspace_id, chunks[])` — batches of 100
- `search(workspace_id, vector, top_k, score_threshold, website_id?)` — Qdrant `query_points` with `with_payload`
- `delete_by_website(workspace_id, website_id)` — `points_selector` filter
- `delete_collection(workspace_id)` — on workspace hard-delete
- `get_collection_info(workspace_id)` — `get_collection`
