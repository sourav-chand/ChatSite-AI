# ChatSite AI

Multi-tenant SaaS that turns any website into an AI-powered chatbot with RAG over Qdrant, SSE streaming, lead capture, and analytics.

## Stack

- **Frontend**: Angular 20+ (standalone components, signals), Angular Material, Tailwind, ApexCharts
- **Backend**: FastAPI 0.115+ (async), SQLAlchemy 2.0, Alembic, Pydantic v2, Celery 5
- **Databases**: PostgreSQL 17, Qdrant (one collection per workspace), Redis 7
- **AI**: OpenAI (gpt-4o + text-embedding-3-small), Google Gemini fallback, sentence-transformers reranker
- **Infra**: Docker Compose, Nginx, GitHub Actions, structlog JSON logging

## Repository layout

```
backend/      FastAPI app, Celery worker, Alembic migrations
frontend/     Angular 20 dashboard
widget/       Vanilla-JS embeddable chat widget
nginx/        Reverse proxy + SSL config
docs/         Architecture, ER diagram, OpenAPI, deployment guide
.github/      CI/CD workflows
docker-compose.yml   dev + prod profiles
```

## Local development

```bash
cp backend/.env.example backend/.env
docker compose --profile dev up -d
# Backend:    http://localhost:8000
# Frontend:   http://localhost:4200
# Flower:     http://localhost:5555
```

Apply migrations:

```bash
docker compose exec backend alembic upgrade head
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Authentication flow](docs/AUTH_FLOW.md)
- [ER diagram](docs/ER_DIAGRAM.md)
- [Qdrant schema](docs/QDRANT_SCHEMA.md)
- [OpenAPI spec](docs/openapi.yaml)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Widget README](widget/README.md)

## License

Proprietary. © 2026 ChatSite AI.
