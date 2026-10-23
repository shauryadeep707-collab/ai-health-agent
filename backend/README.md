# AI Health Agent — Backend Architecture & API Guide

This directory houses the Python Flask application, RESTful routes, security layers, database repositories, AI engine integrations, and external DigiLocker/API Setu gateways.

---

## 1. Directory Structure

```text
backend/
├── app.py                     # Flask application factory (create_app), blueprints, static file server, error handlers
├── config.py                  # Central configuration loaded from .env
├── requirements.txt           # Production and testing Python dependencies
├── routes/
│   ├── auth_routes.py         # Registration, login, session inspection, consent recording
│   ├── doctor_routes.py       # DigiLocker flow initiation, OAuth2 callback, verification status, sandbox testing
│   ├── patient_routes.py      # Profile management, medical report upload, lab extraction, parameter trends
│   ├── ai_routes.py           # Multi-turn health consultation chat, emergency screening, doctor sharing
│   ├── appointment_routes.py  # Doctor directory search, slot booking, appointment lifecycle
│   ├── medicine_routes.py     # Medicine search, pharmacology details, drug interaction checker
│   └── product_routes.py      # Health product catalog search with spelling suggestions
├── services/
│   ├── digilocker_service.py  # DigiLocker / API Setu OAuth2 client, PKCE/nonce, token exchange, sandbox simulator
│   ├── doctor_verification_service.py # Fuzzy name similarity, registration normalization, 4-tier state machine
│   ├── report_analysis_service.py     # PDF text extraction (pypdf), regex lab value parser, reference intervals, AI explanations
│   ├── ai_health_service.py   # Red-flag emergency detector, conversational triage, medical safety constraints
│   ├── medicine_service.py    # Drug information lookup, pairwise interaction matrix
│   └── product_service.py     # Product search and fuzzy spelling correction
├── database/
│   ├── connection.py          # Database abstraction supporting Oracle Database (oracledb) and SQLite local fallback
│   └── repositories.py        # Data Access Layer (Users, Doctors, Verifications, Reports, Appointments, etc.)
├── security/
│   ├── auth.py                # BCrypt password hashing, PyJWT tokens, @jwt_required, @verified_doctor_required
│   ├── validation.py          # Input sanitization, email/phone regex, file upload magic bytes validation
│   ├── rate_limiter.py        # In-memory token bucket rate limiting for sensitive endpoints
│   └── audit.py               # Immutable audit logging helper for security and clinical operations
└── tests/
    └── test_ai_health.py      # Automated pytest suite covering auth, verification, OCR extraction, and medical safety
```

---

## 2. DigiLocker Doctor Verification State Machine

The verification subsystem (`backend/services/doctor_verification_service.py`) processes credentials returned from DigiLocker / API Setu:

| Status | Trigger Condition | Doctor Privileges Granted? |
| :--- | :--- | :--- |
| **`PENDING`** | Verification flow initiated but document not yet fetched or processed | ❌ No (Read-only portal) |
| **`VERIFIED`** | Document authentic, Registration Number matches, and Name Similarity $\ge 85\%$ | ✅ Yes (Can accept appointments and view shared patient records) |
| **`REVIEW_REQUIRED`**| Inconclusive result, Name Similarity between $40\%$ and $84\%$ (e.g. maiden name variation), or council jurisdiction mismatch | ❌ No (Flagged for administrative review; not labeled as fake) |
| **`REJECTED`** | Sufficient negative evidence: invalid registration number, revoked license, or completely different doctor | ❌ No |

---

## 3. Modular AI Engine (Gemini / Ollama / Clinical Rules)

The AI layer (`backend/services/report_analysis_service.py` and `backend/services/ai_health_service.py`) supports hot-swapping providers via `.env`:

1. **Google Gemini API (`AI_PROVIDER=gemini`):**
   - Connects to Google Generative AI endpoints using `GEMINI_API_KEY`.
   - Generates compassionate, plain English explanations of laboratory metrics.
2. **Ollama (`AI_PROVIDER=ollama`):**
   - Connects to local self-hosted models (e.g. `meditron` or `llama3`) via `OLLAMA_BASE_URL`.
3. **Clinical Rules Engine (Deterministic Fallback):**
   - Operates offline with zero external network dependencies.
   - Computes lab variance, flags high/low values, and enforces mandatory non-diagnostic disclaimers.

---

## 4. Security & Privacy Safeguards

- **Magic Bytes Validation:** Uploaded files are inspected for true binary headers (`%PDF-`, `\x89PNG`, `\xff\xd8\xff`) to block extension spoofing attacks.
- **Role-Based Access Control:** Unverified doctors are blocked from accessing patient medical records.
- **Audit Logging:** Verification events, report uploads, and consultation sharings are logged in `AUDIT_LOGS`.
- **Rate Limiting:** Prevents brute force on login and registration endpoints.
- **No Token Retention:** DigiLocker OAuth access tokens are discarded immediately after document retrieval.

---

## 5. Running the Backend

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Run test suite
pytest -v

# 3. Start development server
python backend/app.py
```
The server will start at `http://127.0.0.1:5000/`.
