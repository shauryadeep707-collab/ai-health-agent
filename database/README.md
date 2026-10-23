# AI Health Agent — Database Setup & Architecture Guide

This directory contains the database definition, normalization architecture, and seed data for the **AI Health Agent** application.

---

## 1. Database Architecture & Schema Overview

The database is normalized to 3NF and enforces strict referential integrity, constraints, indexes, and audit controls for sensitive medical information:

1. **`USERS`**: Identity and login authentication table (email, bcrypt hash, role: `PATIENT` | `DOCTOR` | `ADMIN`, activity flag).
2. **`PATIENT_PROFILES`**: Patient demographics, emergency contacts, blood group, allergies, and chronic medical history.
3. **`DOCTOR_PROFILES`**: Medical qualifications, registration number, state medical council, jurisdiction, specialty, consultation fee, and `verification_status` (`PENDING`, `VERIFIED`, `REVIEW_REQUIRED`, `REJECTED`).
4. **`DOCTOR_VERIFICATIONS`**: DigiLocker / API Setu audit trail, document URI, issuer ID, extracted credential fields, fuzzy match score, and review history.
5. **`MEDICAL_REPORTS`**: Uploaded diagnostic files metadata (PDF/image), OCR text, confirmation status.
6. **`REPORT_ANALYSES`**: AI explanation breakdown, plain English summary, non-diagnostic safety notes, risk level, abnormal counter.
7. **`REPORT_TEST_VALUES`**: Extracted lab parameters, measured numerical values, units, reference intervals, and flags (`NORMAL`, `LOW`, `HIGH`, `CRITICAL`).
8. **`CONSULTATIONS`**: Conversational sessions between patient and AI or doctor, risk categorization, and sharing authorization.
9. **`CONSULTATION_MESSAGES`**: Chat dialogue history with sender tags (`PATIENT`, `AI_ASSISTANT`, `DOCTOR`, `SYSTEM`).
10. **`MEDICINE_INFORMATION`**: Therapeutic classes, approved uses, safety precautions, contraindications, and verified pharmacy links.
11. **`DRUG_INTERACTIONS`**: Clinical pairwise drug interaction severity warnings and doctor advice.
12. **`HEALTH_PRODUCTS`**: Approved diagnostic devices and OTC wellness items with search tags and demo badges.
13. **`APPOINTMENTS`**: Booking slots, statuses (`BOOKED`, `CONFIRMED`, `CANCELLED`, `COMPLETED`), and doctor visit notes.
14. **`USER_CONSENTS`**: Explicit consent tracking for health data processing and privacy policy.
15. **`AUDIT_LOGS`**: Immutable audit logs capturing security events, verification actions, and report accesses.

---

## 2. Oracle SQL Deployment Instructions

### Prerequisites
- Oracle Database 19c, 21c, 23ai, Oracle Express Edition (XE), or Oracle Autonomous Database (ATP).
- `sqlplus`, `sqlcl`, Oracle SQL Developer, or DBeaver.

### Step-by-Step Execution:
1. Connect to your Oracle Pluggable Database (PDB) as a privileged user (e.g., `SYSTEM` or `ADMIN`):
   ```bash
   sqlplus system/YourPassword@localhost:1521/XEPDB1
   ```

2. Create the application user/schema:
   ```sql
   CREATE USER ai_health_user IDENTIFIED BY "YourStrongOraclePasswordHere123#";
   GRANT CONNECT, RESOURCE, CREATE VIEW, UNLIMITED TABLESPACE TO ai_health_user;
   EXIT;
   ```

3. Run the schema creation script:
   ```bash
   sqlplus ai_health_user/"YourStrongOraclePasswordHere123#"@localhost:1521/XEPDB1 @database/schema.sql
   ```

4. Populate sample seed data:
   ```bash
   sqlplus ai_health_user/"YourStrongOraclePasswordHere123#"@localhost:1521/XEPDB1 @database/sample_data.sql
   ```

---

## 3. Connecting Flask to Oracle Database via `python-oracledb`

The backend connects using `python-oracledb` (the official Oracle driver for Python).

### Thin Mode (Default — Zero Client Installation Required)
By default, `python-oracledb` runs in **Thin mode**, which connects directly to Oracle Database without needing Oracle Client libraries installed on your machine:
```python
import oracledb

connection = oracledb.connect(
    user="ai_health_user",
    password="YourStrongOraclePasswordHere123#",
    dsn="localhost:1521/XEPDB1"
)
```

### Oracle Autonomous Cloud Database (Wallet / mTLS)
If using Oracle Cloud Free Tier Autonomous Database:
1. Download the Client Credentials zip (`Wallet_*.zip`) from OCI Console.
2. Unzip into a folder (e.g., `C:/oracle/wallet` or `/opt/oracle/wallet`).
3. Set environment variables in `.env`:
   ```ini
   DB_TYPE=oracle
   ORACLE_USER=admin
   ORACLE_PASSWORD=YourAutonomousDbPassword
   ORACLE_DSN=myhealthdb_high
   ORACLE_CONFIG_DIR=C:/oracle/wallet
   ORACLE_WALLET_PASSWORD=YourWalletPassword
   ```

---

## 4. Dual-Mode Local Developer Fallback (SQLite)

To allow instant zero-friction local development, automated testing, and CI without requiring a running Oracle Database instance, the backend database layer (`backend/database/connection.py`) features a **Dual-Mode Adapter**:

- When `DB_TYPE=sqlite` (default in `.env`), the backend automatically initializes an embedded SQLite database (`database/ai_health.db`) with an identical schema and seeds the full dataset.
- When `DB_TYPE=oracle`, the backend seamlessly routes all transactions to `python-oracledb` using connection pooling.
- All SQL repositories use ANSI-compliant parameterized queries compatible with both engines.
