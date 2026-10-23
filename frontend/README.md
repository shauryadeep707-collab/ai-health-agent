# AI Health Agent — Frontend Architecture & UI Guide

This directory houses the presentation tier for the **AI Health Agent** web platform. It is built strictly using **HTML5, CSS3, and Vanilla JavaScript** without dependencies on React, Next.js, or client-side bundlers.

---

## 1. Directory Structure

```text
frontend/
├── index.html                 # Public landing page, features, medical disclaimer, and stats
├── patient-login.html         # Patient authentication portal
├── patient-register.html      # Patient registration with explicit health & privacy consent
├── doctor-login.html          # Doctor authentication portal
├── doctor-register.html       # Doctor registration with DigiLocker verification button
├── patient-dashboard.html     # Tabbed patient dashboard (Profile, AI Chat, Reports, Doctors, Appointments, Medicines, Products)
├── doctor-dashboard.html      # Doctor dashboard (DigiLocker status, appointment manager, shared patient records)
├── report-analysis.html       # Deep-dive medical report viewer, parameter breakdown, and trend comparison
├── health-chat.html           # Dedicated AI conversational health triage assistant
├── doctor-search.html         # Search verified practitioners by specialty, council, and location
├── appointments.html          # Appointment booking & schedule management
├── medicine-search.html       # Authoritative medicine directory & drug-drug interaction checker
├── css/
│   ├── style.css              # Core clinical design system, typography, colors, navigation, badges, modals
│   ├── dashboard.css          # Dashboard layouts, sidebar, chat bubbles, report tables, stats cards
│   └── forms.css              # Form controls, validation states, dropzones, DigiLocker button
└── js/
    ├── auth.js                # JWT session management, route guarding, login/logout, user state
    ├── doctor-verification.js # DigiLocker OAuth2 initiation, sandbox simulation, and status polling
    ├── report-upload.js       # Drag-and-drop file upload, lab value extraction table, confirmation, AI summary
    ├── health-chat.js         # Conversational AI triage, emergency red flag banner, follow-up chips, share modal
    └── appointments.js        # Doctor search, appointment scheduling modal, and booking actions
```

---

## 2. Key Pages & Workflows

### 1. Patient Portal (`patient-dashboard.html`)
- **AI Health Assistant:** Interactive conversational triage assistant with real-time red flag screening and doctor sharing.
- **Medical Report Analysis:** Drag-and-drop PDF/image uploader. Extracts lab values, compares against standard reference ranges, and provides plain English AI explanations with non-diagnostic disclaimers.
- **Longitudinal Trend Comparison:** Allows patients to input a parameter (e.g. `Total Cholesterol` or `HbA1c`) to visualize variations across consecutive reports.
- **Find Doctors & Schedule Appointments:** Filter doctors by specialty, jurisdiction, and consultation fee. Real-time booking slots.
- **Medicine Compendium & Interaction Checker:** Search medications with approved uses and contraindications, test pairwise combinations for adverse interactions, and view legitimate pharmacy links (Tata 1mg, Apollo Pharmacy, Netmeds).
- **Health Products Catalog:** Browse diagnostic devices (BP monitors, glucometers, pulse oximeters) with spell-checking and demo data badges.
- **Privacy & Consents:** View and manage statutory consents for health data processing and privacy policies.

### 2. Doctor Portal (`doctor-dashboard.html`)
- **DigiLocker Medical Registration Verification:** Prominent verification card displaying current status (`PENDING`, `VERIFIED`, `REVIEW_REQUIRED`, `REJECTED`), registration metadata, identity match score, and issuer info.
- **Verification Actions:**
  * **Verify with DigiLocker:** Initiates authorized OAuth2 flow to pull official council certificate.
  * **Test DigiLocker Sandbox:** Opens sandbox simulator to test exact match, name variation, or registration mismatch scenarios.
  * **Request Council Review:** Submits manual administrative review request for councils not yet digitized on DigiLocker.
- **Appointment Manager:** Review booking requests, confirm, reschedule, or mark completed.
- **Authorized Patient Consultations:** Access medical records and AI consultation transcripts shared explicitly by patients.

---

## 3. Communication with the Backend

All Vanilla JS modules communicate with Flask REST APIs via `Auth.fetchWithAuth()` in `frontend/js/auth.js`:
- Automatically passes `Authorization: Bearer <jwt_token>` header.
- Intercepts `401 Unauthorized` responses to redirect expired sessions cleanly to login.
- Respects role-based access control (`@role_required` and `@verified_doctor_required`).

To serve the frontend directly, launch the Flask backend (`python backend/app.py`), which statically hosts all frontend assets at `http://127.0.0.1:5000/`.
