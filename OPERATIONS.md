# Blood Hub: Production Operations & Maintenance Manual

This document outlines daily operational maintenance, backup procedures, health monitoring, and disaster recovery.

---

## 1. System Health Monitoring

### 1.1 Health Endpoint
Blood Hub exposes an authoritative health endpoint at `/health`:
```bash
curl -s http://localhost:8000/health | jq
```
Expected response:
```json
{
  "status": "healthy",
  "service": "Blood Hub",
  "version": "1.0.0",
  "environment": "production",
  "database": "connected",
  "timestamp": "2026-09-21T04:15:50Z"
}
```

### 1.2 Service Logs
```bash
# Stream API logs
docker compose logs -f bloodhub-api

# Stream Worker logs
docker compose logs -f bloodhub-worker
```

---

## 2. Backup & Disaster Recovery

### 2.1 Automated SQLite / PostgreSQL Backup
For SQLite:
```bash
sqlite3 /data/bloodhub.db ".backup '/data/backup_$(date +%Y%m%d_%H%M%S).db'"
```

For PostgreSQL:
```bash
pg_dump -U bloodhub_user -d bloodhub | gzip > /backups/bloodhub_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 2.2 Recovery Procedure
1. Stop the application services:
   ```bash
   docker compose stop bloodhub-api bloodhub-worker
   ```
2. Restore the database file or import the SQL dump:
   ```bash
   cp /data/backup_20260921.db /data/bloodhub.db
   ```
3. Restart services:
   ```bash
   docker compose start
   ```

---

## 3. Background Worker Operations
The background worker (`scripts/run_worker.py`) executes an authoritative sweep every 5 seconds:
- **Wave Timeouts**: Advances expired active waves to the next concentric radius.
- **Offer Reconciliations**: Frees donors whose offers timed out without response back to `AVAILABLE`.
- **Request Expirations**: Marks requests older than 24 hours as `EXPIRED`.
