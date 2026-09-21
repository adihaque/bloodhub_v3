# Blood Hub: Production Deployment Guide

This guide describes deploying Blood Hub on a standard Ubuntu Linux VPS (DigitalOcean, Hetzner, AWS, Linode) or any container host.

---

## Option 1: Docker Compose Deployment (Recommended)

1. Copy repository files to server:
   ```bash
   git clone <repo_url> /opt/bloodhub
   cd /opt/bloodhub
   ```
2. Configure `.env`:
   ```bash
   cp .env.example .env
   # Update SECRET_KEY with: openssl rand -hex 32
   ```
3. Build and launch containers:
   ```bash
   docker compose up -d --build
   ```
4. Seed initial institutional blood banks and admin account:
   ```bash
   docker compose exec bloodhub-api python3 scripts/seed_data.py
   ```
5. Verify health:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Option 2: Nginx Reverse Proxy & Let's Encrypt TLS

Configure Nginx reverse proxy block:
```nginx
server {
    listen 80;
    server_name bloodhub.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bloodhub.example.com;

    ssl_certificate /etc/letsencrypt/live/bloodhub.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bloodhub.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
