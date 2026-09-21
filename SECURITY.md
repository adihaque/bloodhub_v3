# Blood Hub: Security Model & Threat Assessment

Blood Hub handles sensitive health information, real-time geographic coordinates, and direct emergency contact details. This document defines the security architecture and protections against fraud and abuse.

---

## 1. Threat Model & Mitigations

### 1.1 Donor Privacy & Anti-Doxxing
- **Location Fuzzing**: Donor residential coordinates are never exposed to arbitrary users. Exact coordinates are fuzzed within an 800-meter jitter radius during candidate searching.
- **Contact Masking**: A donor's phone number is strictly private until they explicitly accept an incoming emergency offer and obtain the assignment lock.

### 1.2 Race Condition & Double-Claiming Attack
- **Threat**: Two malicious or competing clients attempt to claim a single blood unit allocation simultaneously.
- **Mitigation**: Database-level atomic locking (`SELECT FOR UPDATE` / mutex transaction) serializes incoming requests. Competing offers are marked `REVOKED` in the same transaction block as the winner's commitment.

### 1.3 Request Flooding & Fake Requests
- **Mitigation**: Requesters must verify their phone number via SMS OTP. Requests require valid hospital coordinates and are rate-limited to prevent automated spamming.

### 1.4 Administrative Accountability
- **Immutable Audit Logging**: Every administrative action (suspending a user, modifying policies, confirming donations) writes an immutable record to the `audit_logs` table recording user ID, IP address, timestamp, action, and resource details.

---

## 2. Authentication & Authorization

### 2.1 Password Security
- Passwords are hashed using **PBKDF2-HMAC-SHA256** with 100,000 iterations and a cryptographically secure 16-byte random salt generated via `secrets.token_hex(16)`.

### 2.2 Token Management
- Short-lived HS256 JSON Web Tokens (JWT) are issued upon authentication with an explicit expiration timestamp (`exp`), role verification, and subject claim (`sub`).

### 2.3 Role-Based Access Control (RBAC)
- **DONOR**: Can update their own availability, update their location, view incoming offers, accept/reject offers. Cannot access other donors' contact details.
- **REQUESTER**: Can create blood requests, view their own request's progress, cancel their requests.
- **ADMIN**: Can view system-wide audit logs, suspend abusive accounts, add verified blood centers, view platform metrics.
