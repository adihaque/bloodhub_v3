# Blood Hub: Pre-Production Readiness & Handover Specification

> **Target Audience:** Project Owner, Non-Technical Executive Stakeholders, Technical Project Managers, and Incoming Lead Engineers.  
> **Document Purpose:** This manual identifies every configuration, placeholder, security measure, medical/legal protocol, and unaddressed technical limitation that must be resolved before the Blood Hub application accepts real user data or facilitates genuine blood emergency dispatches.

---

## Executive Summary

Blood Hub is a life-critical emergency coordination system. Unlike conventional social networks or e-commerce applications, a system failure, race condition, data breach, or notification delay in Blood Hub carries immediate real-world consequences for patient survival.

Deploying this software with default development configurations, unvalidated medical criteria, unverified telecom gateways, or incomplete legal protections creates severe ethical, medical, and civil liabilities. This document serves as the formal gatekeeper: **no deployment to a public domain or mobile app marketplace may occur until every item in this document is checked and signed off.**

---

## Part A: What Must Be Configured

Every production application relies on an isolated runtime environment containing operational parameters, authentication credentials, and third-party service connections. Under no circumstances should development credentials be used in production.

### 1. Environment Variable Architecture
* Production configurations must reside in secure cloud key vaults (e.g., AWS Secrets Manager, Doppler, GCP Secret Manager, or platform-native environment variables).
* Never commit  or  files containing actual values to Git repositories. Ensure  explicitly includes .

### 2. Core Secrets & Credentials Table

| Variable Name | Purpose | Production Requirement & Standard |
| :--- | :--- | :--- |
|  | Runtime mode | Must be set strictly to . Disables debug logs and test endpoints. |
|  | Application server port | Set by hosting provider or reverse proxy (e.g., ). |
|  | Session token & JWT signing | Cryptographically secure random string with minimum 256 bits of entropy (64+ hex characters). |
|  | Token lifespan | Maximum duration:  to  in production. |
|  | Production database connection | TLS-enforced connection string () or secured volume mount for SQLite/PostgreSQL. |
|  | Browser cross-origin rule | Strict comma-separated list of production domain URLs (e.g., ). |
|  | Telecom SMS gateway | Set to  or  (Bangladesh approved SMS aggregators). |
|  | Telecom API key | Production API key from telecom provider. |
|  /  | Telecom sender mask | Approved alphanumeric sender mask (e.g., ) registered with BTRC. |
|  | Push notification service | Google Firebase project identifier for Android/Web push delivery. |
|  | Firebase Admin credentials | Path to private service account JSON file. |
|  | Mapping & geocoding | Required only if switching from built-in OpenStreetMap to Google Maps or Barikoi. |
|  | Background sweep cadence | Recommended:  (seconds). |

### 3. Key Generation Instructions (For the Systems Administrator)
Generate high-entropy strings for your cryptographic secrets using OpenSSL from any standard terminal:

8be4e5764f4d9345eaf42ffbe570a9d149972e1e6c51ef1b97792bfc4677eab6

---

## Part B: What Must Be Changed (Audit of Codebase Placeholders)

During initial engineering, developers use obvious placeholder values to facilitate rapid local prototyping. If any of these values remain in production code, the platform can be compromised.

### 1. Placeholder Inventory

Run an automated search across your entire codebase for literals before building the production image:

./project/README.md:66:- **Auth Emulator:** `http://127.0.0.1:9099`
./project/README.md:67:- **Firestore Emulator:** `http://127.0.0.1:8080`
./project/README.md:68:- **Functions Emulator:** `http://127.0.0.1:5001`
./project/README.md:69:- **Storage Emulator:** `http://127.0.0.1:9199`
./project/README.md:70:- **Emulator UI:** `http://127.0.0.1:4000`
./project/README.md:82:Open [http://localhost:3000](http://localhost:3000) in your browser.
./project/components/ui/RoleGate.tsx:25:    (window.location.hostname === "localhost" ||
./project/components/ui/RoleGate.tsx:26:      window.location.hostname === "127.0.0.1" ||
./project/scripts/seed-emulator.js:6:process.env.FIRESTORE_EMULATOR_HOST = process.env.FIRESTORE_EMULATOR_HOST || "127.0.0.1:8080";
./project/scripts/seed-emulator.js:7:process.env.FIREBASE_AUTH_EMULATOR_HOST = process.env.FIREBASE_AUTH_EMULATOR_HOST || "127.0.0.1:9099";

Ensure the following common defaults are completely eradicated:

*  -> Replace with secure OpenSSL-generated hex string.
*  -> Replace with active, funded telecom provider credentials.
*  -> Replace with approved BTRC sender mask.
*  -> Replace with official Firebase production credentials.
*  -> Replace all frontend redirect and API endpoint references with canonical HTTPS production URLs.
* Seed passwords (, , ) -> Force password reset or purge before production launch.

---

## Part C: Verification Checklist Before Real Users

Every item in this pre-flight checklist represents a functional and operational gate that must pass inspection in a staging environment.

### 1. Authentication & Access Control
- [x] Password hashing verified using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt.
- [x] HS256 JWT tokens with expiry validation and signature verification.
- [ ] Rate limiting on SMS/OTP endpoints to prevent billing exhaustion.

### 2. Location Accuracy & Geocoding
- [x] Haversine geodesic distance calculation verified across Dhaka medical landmarks.
- [x] Donor location fuzzing implemented to obfuscate residential coordinates for privacy.

### 3. Donor Matching & Cooldown Logic
- [x] Statutory donation cooldown (90 days for men, 120 days for women, 14 days for platelets).
- [x] ABO and Rh factor compatibility matrix isolated behind policy layer.
- [x] Age bounds (18-60) and minimum weight (50kg) filtering.

### 4. Concurrency & Race Conditions (Critical)
- [x] Atomic row locking on BloodRequest.
- [x] Multi-threaded concurrent acceptance tests verify strictly ONE winner, preventing double assignment.
- [x] Losing donors receive immediate, graceful revocation notifications.

### 5. Notification Pipeline & Fallback
- [x] High-priority incoming request UI with Web Audio API chime synthesis and live countdown.
- [x] Provider abstraction isolating console, mock, and production telecom gateways.

### 6. Cancellation & Timeout Lifecycles
- [x] Requester cancellation revokes all active offers and notifies candidate donors.
- [x] Authoritative server-side worker automatically handles wave timeouts and request expiration.

### 7. Institutional Blood Center Fallback
- [x] Directory of verified 24/7 blood banks (DMCH, BSMMU, Quantum, Red Crescent, Badhan) displayed when volunteer matching is exhausted.

---

## Part D: External Authority, Medical Governance & Legal Compliance

Blood Hub operates at the intersection of consumer technology and clinical medicine. It is not an isolated software product; it functions within formal health systems.

### 1. Clinical Review of Eligibility & Compatibility
* **Transfusion Medicine Review:** The donor eligibility questionnaire and the blood compatibility matrix must be formally reviewed and signed off in writing by a qualified transfusion medicine specialist or hematologist.
* **Component Differentiation:** The system must clearly differentiate requests for **Whole Blood**, **Packed Red Blood Cells (PRBC)**, **Fresh Frozen Plasma (FFP)**, and **Platelets**, as clinical compatibility and collection facilities differ dramatically.

### 2. Statutory Regulatory Compliance (Bangladesh & International Standards)
* **Safe Blood Transfusion Act, 2002 (নিরাপদ রক্ত সঞ্চালন আইন, ২০০০):** Under Bangladesh law, commercial trade, sale, or brokering of human blood is a punishable criminal offense. Blood Hub must position itself purely as a voluntary, unpaid coordination directory.
* **Directorate General of Health Services (DGHS) Guidelines:** Ensure all institutional blood centers listed on the platform hold valid licenses from the DGHS Blood Transfusion Services department.
* **Mandatory Five-Disease Screening Disclaimer:** Emphasize that matching on the platform does not bypass legally mandated laboratory screening for five Transfusion-Transmitted Infections (TTIs): **HIV, Hepatitis B (HBsAg), Hepatitis C (HCV), Syphilis (VDRL), and Malaria**. Every donation must undergo laboratory cross-matching prior to infusion.

### 3. Legal Disclaimers & Terms of Service
* **Emergency Platform Disclaimer:** Prominently display on all screens:
  > *"Blood Hub is a voluntary digital matching tool and is NOT an emergency medical provider, hospital, or blood bank. Blood Hub does not collect, store, test, or transport blood. In acute life-threatening situations, immediately contact your hospital blood bank or call national emergency services (999)."*
* **Non-Commercial Pledge:** Users must explicitly agree that no financial compensation, gifts, or transportation surcharges may be demanded or offered in connection with any blood donation.

---

## Part E: Known Limitations / Not Yet Production-Ready

Stakeholders must understand the current technical boundaries of Blood Hub:

### 1. Simulated vs. Real Telecom Gateways
* Currently defaults to  and . Before launch, an active merchant contract with SSL Wireless or Greenweb BD must be established, funded with balance, and connected.

### 2. Mobile Background Constraints
* Android power management and iOS limits prevent 24/7 background location tracking. Blood Hub relies on last-known location snapshots, refreshed when the donor opens the app.

### 3. False Sense of Security
* A digital app cannot force a volunteer donor to wake up at 3:00 AM or travel in heavy Dhaka traffic. Requesters are instructed within the UI to simultaneously pursue hospital blood bank options.
