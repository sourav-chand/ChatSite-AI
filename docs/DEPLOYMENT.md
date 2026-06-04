# ChatSite AI — Production Deployment Guide

## 0. Prerequisites

- Ubuntu 22.04+ server (2 vCPU / 4 GB RAM minimum, 8 GB recommended)
- Docker Engine 24+ and Docker Compose v2
- A registered domain (e.g. `chatsite.ai`)
- OpenAI API key
- SMTP credentials (SendGrid, SES, etc.)
- Stripe account (for paid plans)

## 1. Server setup

```bash
sudo apt update && sudo apt install -y ufw fail2ban
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```

## 2. SSL via Let's Encrypt

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d api.chatsite.ai -d app.chatsite.ai
sudo mkdir -p /opt/chatsite/nginx/certs /opt/chatsite/nginx/private
sudo cp /etc/letsencrypt/live/api.chatsite.ai/fullchain.pem /opt/chatsite/nginx/certs/chatsite.crt
sudo cp /etc/letsencrypt/live/api.chatsite.ai/privkey.pem /opt/chatsite/nginx/private/chatsite.key
```

Add a cron job for renewal:

```cron
0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/api.chatsite.ai/* /opt/chatsite/nginx/certs/ /opt/chatsite/nginx/private/ && cd /opt/chatsite && docker compose --profile prod exec -T nginx nginx -s reload
```

## 3. Project deployment

```bash
sudo mkdir -p /opt/chatsite
cd /opt/chatsite
git clone https://github.com/your-org/chatsite-ai.git .
cp backend/.env.example .env
# Edit .env with production values
docker compose --profile prod pull
docker compose --profile prod up -d --no-build
```

## 4. First-boot checks

```bash
docker compose --profile prod ps              # all healthy
docker compose --profile prod logs backend    # no errors
curl https://api.chatsite.ai/health           # {"status":"ok"}
```

## 5. Database migration

Migrations run automatically on backend container start (`alembic upgrade head` in the command). To migrate manually:

```bash
docker compose --profile prod exec backend alembic upgrade head
```

## 6. Observability

- JSON logs: `docker compose logs --tail=200 backend`
- Celery monitoring (dev only): http://server:5555 (flower profile)
- Postgres access: `docker compose exec postgres psql -U chatsite chatsite`

## 7. Backup strategy

```bash
# Daily postgres dump
docker compose exec -T postgres pg_dump -U chatsite chatsite | gzip > /backups/chatsite-$(date +%F).sql.gz
# Qdrant snapshot
docker compose exec qdrant curl -X POST http://localhost:6333/snapshots
```

## 8. Rollback

```bash
cd /opt/chatsite
git pull
# Pin previous SHA in .env
echo "TAG=<previous-sha>" > .env
docker compose --profile prod pull
docker compose --profile prod up -d --no-build
```

## 9. Scaling

- Add more FastAPI workers: increase `--workers 4` in the `backend` command
- Add more Celery workers: `docker compose --profile prod up --scale celery-worker=4`
- Qdrant: switch to a clustered Qdrant deployment (separate compose stack)
- Postgres: promote a read replica and route analytics queries to it via SQLAlchemy binds

## 10. Required environment variables

| Key                    | Notes                                |
|------------------------|--------------------------------------|
| `DATABASE_URL`         | asyncpg DSN                          |
| `QDRANT_URL`           | Internal Qdrant URL                  |
| `REDIS_URL`            | Internal Redis URL                   |
| `OPENAI_API_KEY`       | Production OpenAI key                |
| `JWT_PRIVATE_KEY_PATH` | Path mounted into backend container  |
| `JWT_PUBLIC_KEY_PATH`  | Path mounted into backend container  |
| `STRIPE_SECRET_KEY`    | Live Stripe key                      |
| `STRIPE_WEBHOOK_SECRET`| From Stripe dashboard                |
| `CORS_ORIGINS`         | Comma-separated list of app origins  |
| `EMAIL_*`              | SMTP credentials                     |
| `FRONTEND_URL`         | https://app.chatsite.ai              |
| `WIDGET_CDN_URL`       | https://cdn.chatsite.ai              |
| `ENVIRONMENT`          | `prod`                               |
