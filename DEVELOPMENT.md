# Blood Hub: Local Development Guide

## Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- `curl` or browser for interacting with web UI

---

## Quickstart

### 1. Clone & Enter Directory
```bash
cd blood-hub
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Run Automated Test Suite
```bash
python3 -m unittest discover -s tests
```

### 4. Seed Development Data
```bash
python3 scripts/seed_data.py
```

### 5. Start Application Server
```bash
uvicorn bloodhub.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Start Background Task Worker (In separate terminal)
```bash
python3 scripts/run_worker.py
```

---

## Accessing Web & Mobile Surfaces
- **Landing Page**: [http://localhost:8000/](http://localhost:8000/)
- **Donor Mobile PWA**: [http://localhost:8000/donor](http://localhost:8000/donor)
- **Requester Portal**: [http://localhost:8000/requester](http://localhost:8000/requester)
- **Admin Dashboard**: [http://localhost:8000/admin](http://localhost:8000/admin)
- **Dispatch Simulator**: [http://localhost:8000/simulator](http://localhost:8000/simulator)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
