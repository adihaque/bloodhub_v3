# Blood Hub: Home Real-World Pilot & Owner Operations Guide

> **Target Audience:** Project Owner (Non-Technical), Operations Lead.  
> **Current Mode:** **PILOT (Real Users & Progressive MVP)**  
> **Immediate Focus:** Registering 1–50 real donors from physical mobile phones with persistent database storage, real-time profile updates, and laptop hosting.

---

## 🚀 Quick Setup: Host on Your Laptop & Test from Your Phones

You can run Blood Hub on your laptop and register real donors using your Android phones or iPhones over your home Wi-Fi network.

### 1. Start the Server on Your Laptop
Open your terminal in the `blood-hub` folder and run:
```bash
python3 -m uvicorn bloodhub.main:app --host 0.0.0.0 --port 8000
```
*(Binding to `0.0.0.0` allows devices on your local network to connect to your laptop.)*

### 2. Find Your Laptop's Local IP Address
* **On Windows:** Open Command Prompt and type `ipconfig`. Look for **IPv4 Address** (e.g., `192.168.0.105`).
* **On Mac / Linux:** Open Terminal and type `ifconfig` or `ip a` (e.g., `192.168.1.15`).

### 3. Open the Donor App on Your Mobile Phones
Connect your phones to the same Wi-Fi network as your laptop:
* Open Chrome (or Safari) on Phone 1 and go to:  
  `http://YOUR_LAPTOP_IP:8000/donor`  
  *(Example: `http://192.168.0.105:8000/donor`)*
* Register Donor A with their real name, phone number, optional WhatsApp, blood group, donation preference, and area.
* Tap **"Complete Donor Registration"**. The donor is saved immediately to the persistent database.
* Repeat on Phone 2 for Donor B.

### 4. Admin Dashboard on Your Laptop
Open in your laptop browser:
* **URL:** `http://localhost:8000/admin`
* **Admin Mobile:** `+8801700000000`
* **Admin Password:** `admin123`
*(You will see your newly registered real donors appear with their blood group, phone, WhatsApp, and availability status in real-time!)*

---

## 🛠️ Safe Database Management for the Non-Technical Owner

You do not need programming or database knowledge to inspect, back up, or restore your database. Use the built-in `scripts/db_admin.py` tool.

### 1. Check Real Donors & Database Health
```bash
python3 scripts/db_admin.py check
```
Displays:
* Active environment (`PILOT`)
* Where your database file is saved
* Total real donors registered and how many are currently `AVAILABLE`
* Admin account status

### 2. Back Up Real User Data
Run this before updating software or restarting your computer:
```bash
python3 scripts/db_admin.py backup
```
*Creates an instant, timestamped backup in the `backups/` folder (e.g. `backups/bloodhub_backup_pilot_20260921_085059.sql`).*

### 3. Restore from a Backup
```bash
python3 scripts/db_admin.py restore backups/your_backup_file.sql
```

### 4. Change Admin Password
```bash
python3 scripts/db_admin.py set-admin
```

---

# Blood Hub: Non-Technical Operations Manual & Owner Guide

> **Target Audience:** System Owner, Community Managers, Operations Leads, Non-Technical Administrators.  
> **Purpose:** This guide explains how Blood Hub functions, how to manage day-to-day operations, how to safely configure parameters, and how to recover from emergency technical failures without requiring software engineering expertise.

---

## 1. System Overview: How Blood Hub Works

Blood Hub connects individuals in urgent need of blood with voluntary blood donors and verified institutional blood facilities across Bangladesh.

### The Architecture in Plain English
Think of Blood Hub as four interlocking departments:
1. **The Reception Desk (The Frontend / Web App):** What users see on their phones and browsers. It collects blood requests, presents incoming urgent call prompts to donors, and displays live matching status.
2. **The Dispatch Office (The Backend API):** The centralized brain that validates requests, runs medical compatibility checks, and computes geographical distances.
3. **The Wave Scheduler (The Background Worker):** An automated timekeeper that monitors active waves, counts down expiration seconds, and triggers the next radius wave when needed.
4. **The Safe (The Database):** The repository storing user profiles, donation cooldown intervals, hospital locations, and system audit logs.

---

## 2. The Dispatch Wave Concept Explained

When an emergency blood request is broadcast, notifying 500 donors simultaneously causes chaos:
* Donors get woken up unnecessarily when someone nearby was already available.
* Donors experience "alert fatigue" and eventually uninstall the app.
* Multiple donors may travel to the hospital concurrently for only one needed bag of blood.

To solve this, Blood Hub uses **Concentric Dispatch Waves (The Ripple Model)**:
* **Wave 1 (Immediate Vicinity):** The system searches for compatible, medically eligible donors within **0 to 5 km** of the patient's hospital. It alerts top candidates (e.g., 4 donors) and gives them **25 seconds** to respond.
* **Wave 2 (Extended Neighborhood):** If no donor accepts during Wave 1, the system automatically expands the radius to **8 km**, contacting the next batch of candidates.
* **Wave 3 (Metropolitan Range):** If still unfulfilled, the ripple expands to **15 km**.
* **Wave 4 (Fallback Radius):** Reaches up to **25 km**.
* **Institutional Handover:** If all volunteer waves pass without an acceptance, the application transitions to **Emergency Fallback Mode**, presenting direct telephone links to verified institutional blood banks (Red Crescent, Quantum, DMCH).

---

## 3. How to Start, Stop, and Restart the System

### Viewing System Status
To see if application components are running:
```bash
docker compose ps
# Or check health endpoint:
curl http://localhost:8000/health
```

### Starting the System
```bash
docker compose up -d
# Or locally with Python:
uvicorn bloodhub.main:app --host 0.0.0.0 --port 8000
```

### Stopping the System
```bash
docker compose down
```

### Starting the Background Worker
```bash
python3 scripts/run_worker.py
```

---

## 4. How to Deploy and Update the System

```
[Backup DB] ──► [Git Pull] ──► [Restart Containers] ──► [Verify /health]
```

1. **Take a safety backup first:**
   ```bash
   cp /data/bloodhub.db /data/bloodhub_backup_$(date +%Y%m%d_%H%M%S).db
   ```
2. **Pull latest changes:**
   ```bash
   git pull origin main
   ```
3. **Restart containers:**
   ```bash
   docker compose restart
   ```
4. **Verify operational status:**
   Open `http://your-server-ip:8000/health` in your browser. Ensure `"status": "healthy"`.

---

## 5. How to View Logs and Monitor Health

Logs are the real-time diary of your system:
```bash
# Docker logs
docker compose logs -f bloodhub-api

# Check worker activity
docker compose logs -f bloodhub-worker
```

Normal activity shows:
* `Urgent Request: B+ needed at Square Hospital! Distance: 1.1km. Timeout: 25s.`
* `Offer accepted atomically. Assignment locked.`

---

## 6. How to Create an Admin User or Reset Passwords

You can run the interactive database seeder or use the Python interactive console:
```bash
python3 scripts/seed_data.py
```
This generates:
* Admin account: `+8801700000000` (Password: `admin123`)

---

## 7. How to Add Verified Blood Centers & Institutions

1. Log in to the Admin Dashboard at `http://your-server-ip:8000/admin`.
2. Institutional centers must be verified under DGHS licensing before being flagged active.
3. Centers are exposed to requesters automatically if volunteer waves time out.

---

## 8. How to Tweak Dispatch Wave Configuration

Wave configurations are defined in `bloodhub/core/config.py` under `DEFAULT_WAVES`:
```python
DEFAULT_WAVES = [
    {"wave_number": 1, "radius_km": 5.0, "candidate_count": 4, "timeout_seconds": 25},
    {"wave_number": 2, "radius_km": 8.0, "candidate_count": 6, "timeout_seconds": 25},
    {"wave_number": 3, "radius_km": 15.0, "candidate_count": 10, "timeout_seconds": 30},
    {"wave_number": 4, "radius_km": 25.0, "candidate_count": 15, "timeout_seconds": 35},
]
```
Safe rules:
* Never set timeout below 15 seconds (donors need time to react).
* In dense cities like Dhaka, smaller radii (3-5km) are preferred due to traffic congestion.

---

## 9. How to Shut Down a Compromised Account

If a donor account is reported for abuse or fraudulent location claims:
1. Open Admin Dashboard (`/admin`).
2. Locate the user in the User Directory.
3. Click "Suspend Account".
4. The system immediately sets `is_active = 0`, revokes any open offers, and prevents future matching.

---

## 10. Emergency Recovery from Common Failures

* **Worker Crashed:** The worker is completely stateless and authoritative. Simply restart `python3 scripts/run_worker.py`. On startup, it inspects active waves in the database and automatically resumes expired wave progression.
* **SMS Gateway Out of Balance:** Log in to your SMS gateway portal (SSL Wireless / Greenweb), top up balance, and reload configuration.
* **Database Locked:** Ensure only one process opens the database in exclusive mode. WAL mode enables multiple readers and a single concurrent writer without deadlock.
