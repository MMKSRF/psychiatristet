# CareBridge Telehealth Telegram-Web Bridge (MVP)

A complete, production-ready MVP connecting patients via a **Telegram Bot** (`@psychiatristETbot`) to psychiatrists through a secure **React (Vite) web dashboard**, managed by an **Admin Panel**.

---

## Architecture Overview

```
                      ┌───────────────────────────────┐
                      │   Patient (Telegram Bot)      │
                      │       @psychiatristETbot      │
                      └──────────────┬────────────────┘
                                     │ (Intake & 2-Way Chat)
                                     ▼
                      ┌───────────────────────────────┐
                      │    FastAPI Unified Backend    │
                      │  - Webhook & Auto-Poller      │
                      │  - Case Assignment & Relay    │
                      │  - Local JSON Relational DB   │
                      └──────┬─────────────────┬──────┘
                             │                 │
              REST APIs & JWT│                 │REST APIs & JWT
                             ▼                 ▼
          ┌───────────────────────┐       ┌────────────────────────┐
          │    Admin Dashboard    │       │ Psychiatrist Dashboard │
          │  - Review Intakes     │       │  - Assigned Cases      │
          │  - Assign Clinicians  │       │  - 2-Way Live Chat     │
          │  - Capacity Analytics │       │  - Telegram Relay      │
          └───────────────────────┘       └────────────────────────┘
```

---

## Quick Start (1 Command)

### 1. Start Backend & Bot
From the project root:
```bash
./venv/bin/python run.py
```
> **What happens automatically:**
> - Loads `.env`
> - Initializes relational JSON tables (`patients.json`, `psychiatrists.json`, `messages.json`)
> - Connects to Telegram and automatically begins receiving patient messages and intake!
> - Backend runs on **`http://localhost:8000`** (Swagger docs at `/docs`).

### 2. Start Frontend
In a separate terminal:
```bash
cd frontend
npm run dev
```
> Opens at **`http://localhost:5173`**.

---

## Demo Accounts & Logins

| Role | Username | Password | Notes |
|---|---|---|---|
| **Admin** | `admin` | `hYetbUdypvojTIMdosA7mxHq` | Reviews pending intakes, assigns cases to clinicians |
| **Psychiatrist 1** | `clinician` | `eegdZKsvX6ldqvDsm8cxqzIe` | Dr. Alex Morgan (Adult psychiatry) |
| **Psychiatrist 2** | `clinician2` | `samLeePassword123` | Dr. Sam Lee (Anxiety and mood disorders) |

---

## Telegram Bot & Webhook Options

You can run the bot in either **Polling mode** (default, no public URL needed) or **Webhook mode** (for production or public URLs).

### Option A: Automatic Polling (Default for Local Dev)
Simply running `python run.py` automatically handles polling in the background without needing tunnels or extra terminal tabs.

### Option B: Cloudflare Quick Webhook (One-Command Tunnel)
If you want to use Telegram Webhooks locally without deploying to a cloud server:
```bash
./venv/bin/python -m backend.webhook_manager tunnel
```
This automatically:
1. Creates an HTTPS Cloudflare tunnel (e.g. `https://xyz.trycloudflare.com`).
2. Registers the webhook with Telegram using your secure `TELEGRAM_WEBHOOK_SECRET`.
3. Cleans up and unregisters the webhook when you press `Ctrl+C`.

### Option C: Custom Webhook URL
```bash
# Check current webhook status:
./venv/bin/python -m backend.webhook_manager status

# Register a public HTTPS URL:
./venv/bin/python -m backend.webhook_manager set https://your-domain.com

# Remove webhook to switch back to polling:
./venv/bin/python -m backend.webhook_manager delete
```

---

## 2-Way Message Flow & Intake Walkthrough

1. **Patient Intake:**
   - Patient opens `@psychiatristETbot` and types `/start`.
   - Bot asks for:
     1. Name or pseudonym
     2. Age
     3. Concern / reason for consultation
   - Upon completion, the patient record is saved to `backend/patients.json` with status `"Pending_Assignment"`.

2. **Admin Case Assignment:**
   - Admin logs into `http://localhost:5173/admin`.
   - Admin views the pending intake in the queue and assigns them to an available psychiatrist (e.g. Dr. Sam Lee).
   - The patient is automatically notified on Telegram:
     > *"Good news! An administrator has assigned Dr. Sam Lee to your case. You can now send messages directly in this chat to begin your consultation."*

3. **2-Way Clinical Chat:**
   - Clinician logs into `http://localhost:5173/psychiatrist/dashboard`.
   - Clinician clicks **"Open chat"** on the assigned patient.
   - When the clinician types a message and clicks **Send**:
     - The message is delivered directly to the patient's phone on Telegram.
     - The message is stored in `backend/messages.json`.
   - When the patient types a reply on Telegram:
     - The message is saved to `backend/messages.json`.
     - The clinician's chat view updates automatically.

---

## API Reference

- `POST /api/auth/login`: Authenticate as Admin or Psychiatrist; returns JWT.
- `GET /api/auth/me`: Get current authenticated user session.
- `POST /api/telegram-webhook`: Telegram update receiver (webhook / internal poller).
- `GET /api/admin/pending-patients`: List all patients with `status == "Pending_Assignment"`.
- `GET /api/admin/psychiatrists`: List all psychiatrists and availability status.
- `POST /api/admin/assign-case`: Assigns patient to psychiatrist, sets status to `Active`, and notifies patient via Telegram.
- `GET /api/psychiatrist/{psychiatrist_id}/patients`: List active cases assigned to the clinician.
- `GET /api/chat/{telegram_id}/{psychiatrist_id}`: Chronological 2-way chat history.
- `POST /api/chat/send`: Sends clinician message to patient's Telegram and records to database.
