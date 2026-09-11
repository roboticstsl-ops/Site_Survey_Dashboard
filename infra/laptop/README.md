# Laptop test deployment

This is a test deployment run from a developer laptop (BUILD_SPEC section 12)
— not a permanent public server.

## Start

```
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example ../.env        # fill in MONGODB_URI, JWT_SECRET, FILE_STORAGE_ROOT
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Health checks

```
curl http://localhost:8000/healthz    # process alive
curl http://localhost:8000/readyz     # Atlas reachable
```

## Exposing to phones on the LAN / beyond

Put a TLS-capable reverse proxy (e.g. Caddy, or an approved tunnel) in front
of Uvicorn — never expose `uvicorn --reload`/dev mode directly. Set
`PUBLIC_BASE_URL` and `CORS_ALLOWED_ORIGINS` to match the real origin the
phones/browsers will use.

## Backups

Until a scheduled job exists: periodically export the Mongo Atlas collections
and copy `FILE_STORAGE_ROOT` somewhere durable. Record the backup time, survey
count and file count each time, and restore-test it at least once before
relying on it (BUILD_SPEC section 14).

## Stop

Standard `Ctrl+C` on the Uvicorn process (or stop the service/container if
running managed). No cleanup step required — MongoDB and the file storage
directory are external to the process.
