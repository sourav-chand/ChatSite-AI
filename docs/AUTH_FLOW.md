# Authentication Flow

## Register → Verify → Login → Refresh → Reset

```
                          ┌──────────────────┐
                          │  POST /register  │
                          │  {email, pwd,    │
                          │   full_name}     │
                          └────────┬─────────┘
                                   │ hash(pwd) + is_verified=false
                                   ▼
                          ┌──────────────────┐
                          │   users table    │
                          │   + send verify  │
                          │     email (JWT   │
                          │   24h TTL)       │
                          └────────┬─────────┘
                                   │ click link
                                   ▼
                          ┌──────────────────┐
                          │ /verify-email    │
                          │  → is_verified=1 │
                          └────────┬─────────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │  POST /login     │
                          │  → access (15m)  │
                          │  → refresh (7d)  │
                          │  refresh stored  │
                          │  sha256 in Redis │
                          │  Set-Cookie HT-  │
                          │  Only Secure     │
                          └────────┬─────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │                                         │
              ▼                                         ▼
   ┌──────────────────┐                     ┌──────────────────────┐
   │ access expires   │                     │ refresh expires      │
   │ → /refresh       │                     │ → 401 + re-login     │
   │ rotates refresh, │                     └──────────────────────┘
   │ revokes old in   │
   │ Redis            │
   └──────────────────┘

   Forgot/Reset:
   POST /forgot-password → email with 1h token
   POST /reset-password  → token+new_password → hash updated
```

## Token Shape (RS256 JWT — Access)

```json
{
  "sub": "user_uuid",
  "ws":  "workspace_uuid",
  "role": "OWNER",
  "iat": 1717xxxxxxx,
  "exp": 1717xxxxxxx,
  "iss": "chatsite.ai",
  "aud": "chatsite-api"
}
```

## Refresh Token

Opaque UUID v4. Only the SHA-256 hash is stored in Redis under
`ws:{workspace_id}:refresh:{user_id}:{jti}`. Plaintext is sent to the client
exactly once at issuance and then persisted in an HttpOnly, Secure,
SameSite=Strict cookie.

## Logout

The current refresh token's Redis entry is deleted. The access token remains
valid until natural expiry (15 min). Short access TTL is the threat-model
mitigation.
