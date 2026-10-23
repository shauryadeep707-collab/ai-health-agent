# AI Health Agent — Comprehensive Web Platform

An end-to-end medical guidance platform that empowers patients to understand their laboratory reports, receive safe AI-driven symptom triage, schedule appointments with verified doctors, and explore pharmacology and medical devices.

Features a **DigiLocker / API Setu credential verification gateway** for doctors, enforcing strict statutory anti-fraud standards rather than relying on ordinary file uploads.

> 📖 **Architecture & Flowcharts Guide:** For a detailed, comprehensive breakdown of how every folder and file connects with Mermaid flowcharts, see [**`ARCHITECTURE_AND_FLOW.md`**](file:///c:/Users/shaur/OneDrive/Desktop/ai%20heal/ARCHITECTURE_AND_FLOW.md).

---

## 1. Project Overview & Architecture

The system is designed with strict separation of concerns across presentation, application logic, and database persistence:

```text
ai-health-agent/
├── frontend/                  # HTML5, CSS3, Vanilla JavaScript (No React/Next.js)
│   ├── index.html             # Landing page & emergency notices
│   ├── patient-login.html     # Patient login
│   ├── patient-register.html  # Patient registration with explicit health & privacy consents
│   ├── doctor-login.html      # Doctor login with verification status indicators
│   ├── doctor-register.html   # Doctor registration with DigiLocker verification CTA
│   ├── patient-dashboard.html # Complete patient experience (Profile, AI Chat, Reports, Doctors, etc.)
│   ├── doctor-dashboard.html  # Doctor verification, appointment manager, and authorized records
│   ├── report-analysis.html   # Medical report viewer, lab value extraction & parameter trends
│   ├── health-chat.html       # Full conversational AI health assistant with red-flag detection
│   ├── doctor-search.html     # Practitioner directory & appointment booking
│   ├── appointments.html      # Appointment management
│   ├── medicine-search.html   # Pharmacology references & drug-drug interaction checker
│   ├── css/                   # Design system (style.css, dashboard.css, forms.css)
│   └── js/                    # Application logic (auth.js, doctor-verification.js, report-upload.js, etc.)
├── backend/                   # Python Flask REST API
│   ├── app.py                 # Application factory & static server
│   ├── config.py              # Configuration & environment variables
│   ├── requirements.txt       # Python package dependencies
│   ├── routes/                # Blueprint REST routes (auth, doctor, patient, ai, appointment, medicine, product)
│   ├── services/              # Business logic (digilocker, verification, report_analysis, ai_health, medicine, product)
│   ├── database/              # Database pool & ANSI SQL repositories (Oracle DB & SQLite fallback)
│   ├── security/              # Auth decorators, Bcrypt, PyJWT, magic bytes validation, rate limiter, audit logs
│   └── tests/                 # 18-suite automated pytest verification
├── database/                  # Oracle SQL & SQLite Scripts
│   ├── schema.sql             # Full DDL schema for Oracle Database (19c/21c/23ai/XE)
│   ├── sample_data.sql        # Seed data (verified doctors, patients, reports, medicines, products)
│   └── README.md              # Oracle Database connection & deployment instructions
├── uploads/                   # Secure storage for uploaded medical reports
├── .env.example               # Template for environment variables
├── .env                       # Local development configuration
└── pytest.ini                 # Pytest configuration
```

---

## 2. Technology Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript (Responsive for Desktop, Tablet, and Mobile).
- **Backend:** Python 3.12+, Flask 3.1, RESTful Blueprints, PyJWT, BCrypt.
- **Database:** Oracle Database (via `python-oracledb`) with automatic embedded SQLite fallback for instant zero-friction local development.
- **AI Engine:** Google Gemini API (`gemini-2.5-flash`), Ollama (`meditron`), and an offline deterministic clinical triage fallback.
- **Document & Lab Parsing:** `pypdf`, regex heuristics, standard clinical reference intervals dictionary, binary magic bytes validation.
- **Credential Verification:** DigiLocker / API Setu OAuth 2.0 gateway with PKCE/anti-CSRF protection and sandbox simulator.

---

## 3. DigiLocker Doctor Verification Workflow

In compliance with statutory medical verification guidelines, doctors must authenticate their credentials using the authorized DigiLocker / API Setu flow:

1. **Initiation:** The doctor clicks **"Verify with DigiLocker"** on the registration page or dashboard.
2. **Authorized Redirect:** A cryptographically random `state` token is generated. The doctor is redirected to DigiLocker's official authorization gateway.
3. **Document Fetching:** Upon consent, the Flask callback exchanges the authorization code for an ephemeral token and fetches the doctor's issued Medical Council Registration Certificate (`DOCREG`).
4. **Multi-Tier State Machine:**
   - **`VERIFIED`:** Registration number confirmed and doctor's name matches ($\ge 85\%$). Verified doctor privileges granted.
   - **`REVIEW_REQUIRED`:** Name variation ($40\% - 84\%$, e.g. maiden name), or state council jurisdiction requires manual check. (Inconclusive results are **never** automatically rejected).
   - **`REJECTED`:** Decisive negative evidence (revoked certificate, registration number mismatch, or completely different doctor).
   - **`PENDING`:** Initial state awaiting document retrieval.
5. **Sandbox Mode:** For development environments where production DigiLocker API credentials are not yet approved, an interactive sandbox simulator is built directly into the UI to test each state transition (`MATCH`, `NAME_MISMATCH`, `REG_MISMATCH`).

---

## 4. Medical Safety & Clinical Safeguards

- **Emergency Red-Flag Detection:** Active screening for acute life-threatening emergencies (crushing chest pain, shortness of breath, stroke signs like facial droop/slurred speech, heavy hemorrhage). When triggered, immediately renders an emergency banner instructing the patient to dial 112 / 911.
- **Non-Diagnostic Explanations:** Explains laboratory findings in plain English while explicitly reminding patients that abnormal test metrics do not automatically constitute a medical diagnosis.
- **Prescription Safeguard:** The AI assistant is programmatically prevented from prescribing prescription-only antibiotics or scheduled medicines.
- **Patient Privacy & Consent:** Medical reports and consultation sessions can only be accessed by a doctor with explicit authorization granted by the patient.

---

## 5. Quickstart & Installation

### Step 1: Clone & Configure Environment
```bash
# Copy template configuration
cp .env.example .env
```

Review `.env` settings:
- **`DB_TYPE`:** Set to `sqlite` for immediate out-of-the-box local testing, or `oracle` for Oracle Database.
- **`AI_PROVIDER`:** `gemini`, `ollama`, or `rule_based`.
- **`GEMINI_API_KEY`:** Add your key from Google AI Studio (if using Gemini).
- **`DIGILOCKER_CLIENT_ID` / `DIGILOCKER_CLIENT_SECRET`:** Add your API Setu credentials (or leave defaults for Sandbox mode).

### Step 2: Install Python Dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 3: Run Automated Test Suite
```bash
pytest -v
```
*(Runs 18 automated tests verifying auth, DigiLocker state machine, upload security, and medical safety).*

### Step 4: Start the Server
```bash
python backend/app.py
```
Open your browser at **`http://127.0.0.1:5000/`**.

---

## 6. Seed Accounts for Demonstration

| Account Type | Email | Password | Status / Role |
| :--- | :--- | :--- | :--- |
| **Patient** | `rahul.mehta@email.com` | `Password123!` | Active Patient with sample lipid report |
| **Verified Doctor** | `dr.priya.sharma@hospital.org` | `Password123!` | Senior Cardiologist (`VERIFIED` via DigiLocker) |
| **Verified Doctor** | `dr.rajesh.varma@clinic.org` | `Password123!` | Consultant Endocrinologist (`VERIFIED` via DigiLocker) |
| **Pending Doctor** | `dr.anita.deshmukh@medcare.org` | `Password123!` | General Medicine (`PENDING` DigiLocker verification) |

---

## 7. Oracle Database Setup (Production Mode)

When connecting to a production Oracle Database 19c, 21c, 23ai, or Autonomous Database:

1. Update `.env`:
   ```ini
   DB_TYPE=oracle
   ORACLE_USER=ai_health_user
   ORACLE_PASSWORD=YourStrongOraclePasswordHere123#
   ORACLE_DSN=localhost:1521/XEPDB1
   ```
2. Run schema and seed scripts via SQL*Plus or SQLcl:
   ```bash
   sqlplus ai_health_user/"YourStrongOraclePasswordHere123#"@localhost:1521/XEPDB1 @database/schema.sql
   sqlplus ai_health_user/"YourStrongOraclePasswordHere123#"@localhost:1521/XEPDB1 @database/sample_data.sql
   ```
*(Refer to `database/README.md` for Oracle Autonomous Database Wallet and mTLS instructions).*

---

## 8. External API Requirements & Approvals

- **DigiLocker / API Setu Production Credentials:** Requires formal organization registration on [partners.digitallocker.gov.in](https://partners.digitallocker.gov.in) with the "Doctor Medical Council Registration" scope approved by the National Medical Commission (NMC).
- **Google Gemini API:** Requires a valid API key from [aistudio.google.com](https://aistudio.google.com).
- **Pharmacy & Product APIs:** Production live stock queries require merchant affiliate agreements (e.g. Tata 1mg, Apollo Pharmacy API). Demo products are explicitly tagged in the UI.

---

## 9. Security & Compliance Notes

- **Password Security:** Salted BCrypt hashing (10–12 log rounds).
- **Session Tokens:** Signed HS256 JSON Web Tokens with strict expiration.
- **MIME & Magic Bytes:** All uploaded files have their binary headers checked to prevent remote code execution or file extension spoofing.
- **Audit Logging:** Security, verification, and consent actions are permanently recorded in `AUDIT_LOGS`.
- **Disclaimer:** This software is an informational decision-support and workflow system; it does not replace professional medical judgment or formal clinical diagnosis.
