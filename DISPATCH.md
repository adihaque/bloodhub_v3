# Blood Hub: Donor Matching & Wave Dispatch Algorithm

This document provides a complete mathematical and architectural breakdown of the Blood Hub ride-hailing style dispatch engine.

---

## 1. The Dispatch Pipeline Overview

```
REQUEST CREATED
      ↓
Stage 1: Medical Compatibility Filtering (ABO / Rh / Component)
      ↓
Stage 2: Eligibility & Cooldown Screening (90-day cooldown, weight, age)
      ↓
Stage 3: Geospatial Distance Calculation (Haversine Formula)
      ↓
Stage 4: Deterministic Multi-Factor Candidate Ranking (Score 0 - 100)
      ↓
Stage 5: Wave Slicing & Candidate Selection (Top N candidates)
      ↓
Stage 6: Urgent Incoming Alert Broadcast (Audio Chime + Countdown Modal)
      ↓
Stage 7: Atomic Claiming Lock (SELECT FOR UPDATE / Mutex)
      ↓
ACCEPT -> Lock Assignment, Revoke Competing Offers, Connect Parties
TIMEOUT -> Escalate to Next Wave (Expand Radius)
EXHAUSTED -> Fallback to Institutional Blood Banks
```

---

## 2. Mathematical & Algorithmic Details

### 2.1 Stage 1: Compatibility Filtering
Standardized via `bloodhub.domain.compatibility`:
- **Red Blood Cells / Whole Blood**:
  - $O^-$: Universal red cell donor.
  - $AB^+$: Universal red cell recipient.
  - Rh-Negative blood can donate to Rh-Positive, but never vice versa.
- **Platelets / Plasma**:
  - Inverse of red cells: $AB$ is the universal plasma donor; $O$ is universal plasma recipient.

### 2.2 Stage 2: Eligibility Screening
- **Statutory Cooldown**:
  - Whole Blood: Men $\ge 90$ days; Women $\ge 120$ days since last donation.
  - Platelets: $\ge 14$ days since last donation.
- **Weight**: $\ge 50$ kg.
- **Age**: Between $18$ and $60$ years.
- **Availability**: Must be in `AVAILABLE` state and have no active assignment (`active_assignment_id == None`).

### 2.3 Stage 3: Geospatial Haversine Formula
Great-circle distance between hospital $(lat_1, lon_1)$ and donor $(lat_2, lon_2)$:

$$\Delta\phi = 	ext{radians}(lat_2 - lat_1)$$
$$\Delta\lambda = 	ext{radians}(lon_2 - lon_1)$$
$$a = \sin^2\left(rac{\Delta\phi}{2}ight) + \cos(	ext{radians}(lat_1))\cos(	ext{radians}(lat_2))\sin^2\left(rac{\Delta\lambda}{2}ight)$$
$$c = 2 \cdot 	ext{atan2}\left(\sqrt{a}, \sqrt{1-a}ight)$$
$$d = R \cdot c \quad (R = 6371.0 	ext{ km})$$

### 2.4 Stage 4: Deterministic Multi-Factor Ranking
Every eligible candidate within wave radius is evaluated transparently across 4 deterministic factors (Total 100 points):

1. **Compatibility Exactness (Max 40 points)**:
   - Exact blood group match (e.g. $B^+ ightarrow B^+$): **40 points**.
   - Compatible alternative match (e.g. $O^+ ightarrow B^+$): **25 points** (conserves universal stock for rare emergencies).
2. **Proximity Score (Max 35 points)**:
   $$	ext{Points} = 35.0 	imes \left(1.0 - \min\left(rac{	ext{Distance}}{	ext{Wave Radius}}, 1.0ight)ight)$$
3. **Reliability & Response Score (Max 15 points)**:
   $$	ext{Points} = 15.0 	imes 	ext{Reliability Score} \quad (0.0 \le 	ext{Score} \le 1.0)$$
4. **Donation Interval Buffer (Max 10 points)**:
   - $> 180$ days since last donation: **10 points**.
   - $120 - 180$ days: **8 points**.
   - $90 - 120$ days: **6 points**.

Candidates are sorted descending by Total Score.

---

## 3. Wave Configuration & Escalation

Default concentric wave schedule:
- **Wave 1**: Radius $5.0$ km, Candidates $4$, Timeout $25$ seconds.
- **Wave 2**: Radius $8.0$ km, Candidates $6$, Timeout $25$ seconds.
- **Wave 3**: Radius $15.0$ km, Candidates $10$, Timeout $30$ seconds.
- **Wave 4**: Radius $25.0$ km, Candidates $15$, Timeout $35$ seconds.

### Escalation Mechanics
If the timeout countdown reaches zero without an acceptance:
1. Active wave is marked `TIMED_OUT`.
2. Outstanding offers transition to `TIMED_OUT`, and candidate donors' availability status resets to `AVAILABLE`.
3. The background worker or dispatcher generates the next wave with expanded radius.
4. If Wave 4 times out with 0 accepted donors, the request transitions to `UNFULFILLED` and displays the emergency institutional blood banks fallback directory.
