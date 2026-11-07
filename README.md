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

## Quick Start

### Local Development (Host Machine)
```bash
python runserver.py
```
> Runs the backend on **`http://localhost:8000`** and the React frontend on **`http://localhost:5173`** with live reload and polling.

---

## Server Deployment & Mobile Phone Testing (`204.44.66.142`)

When testing on your VPS server (`204.44.66.142`) and accessing via phone over mobile data or external network:

### 1. Run the Server
From the project root on your server:
```bash
python runserver.py
# or: python serverrun.py
```
> **What this does:**
> - Starts the React/Vite frontend on **`0.0.0.0:5173`** and the FastAPI backend on **`0.0.0.0:8000`**.
> - Opens the dashboard at **`http://204.44.66.142:5173`** and login at **`http://204.44.66.142:5173/login`**.
> - Proxies frontend `/api` requests to the backend so the two services communicate without browser CORS issues.
> - Connects to **`fulldb.db`** (lightweight SQLite WAL mode optimized for 1GB RAM).
> - Automatically receives Telegram bot messages via embedded background worker.
>
> Node.js/npm and frontend dependencies are required. If dependencies are not installed yet, run `cd frontend && npm install`.

### 2. Test from Your Mobile Phone
1. Allow inbound TCP ports **5173** (frontend) and **8000** (backend/API) in the server firewall and cloud firewall.
2. Open Chrome or Safari on your phone.
3. Visit: **`http://204.44.66.142:5173`** (or `/login`).
4. Log in with admin or clinician credentials to manage patients, review bilingual intake forms, and chat live with patients on Telegram!

> [!TIP]
> If your phone cannot connect, verify your server's firewall allows both ports:
> `sudo ufw allow 5173/tcp && sudo ufw allow 8000/tcp`

---

## Accounts

Admin and existing development accounts are configured through `AUTH_USERS_JSON` in the local `.env`; do not put real passwords in this README or commit them. Admins can create psychiatrist accounts in the Psychiatrists section of the dashboard. A new psychiatrist signs in with their email and initial password, then must set a new password before accessing clinical features.

Psychiatrist passwords created by the admin panel are stored as salted PBKDF2 hashes. Use a separate, secure channel to share initial passwords.

---

## Telegram Bot & Webhook Options

You can run the bot in either **Polling mode** (default, no public URL needed) or **Webhook mode** (for production or public URLs).

### Option A: Automatic Polling (Default for Local Dev)
Running `python runserver.py` automatically handles polling in the background without needing tunnels or extra terminal tabs.

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
- `POST /api/auth/change-password`: Set a new password for a newly created psychiatrist account.
- `POST /api/telegram-webhook`: Telegram update receiver (webhook / internal poller).
- `GET /api/admin/pending-patients`: List all patients with `status == "Pending_Assignment"`.
- `GET /api/admin/psychiatrists`: List all psychiatrists and availability status.
- `POST /api/admin/psychiatrists`: Create a psychiatrist account with a required initial password.
- `PATCH /api/admin/psychiatrists/{psychiatrist_id}/capacity`: Update a clinician's patient limit.
- `GET /api/admin/psychiatrists/{psychiatrist_id}/patients`: Read-only list of a psychiatrist's active patients.
- `GET /api/admin/interaction-logs`: Read-only message counts and latest activity timestamps; message bodies are not exposed.
- `POST /api/admin/assign-case`: Assigns patient to psychiatrist, sets status to `Active`, and notifies patient via Telegram.
- `GET /api/psychiatrist/{psychiatrist_id}/patients`: List active cases assigned to the clinician.
- `GET /api/chat/{telegram_id}/{psychiatrist_id}`: Chronological 2-way chat history.
- `POST /api/chat/send`: Sends clinician message to patient's Telegram and records to database.
- `GET/POST /api/chat/{telegram_id}/{psychiatrist_id}/notes`: List or create private clinician notes.
- `PATCH/DELETE /api/chat/{telegram_id}/{psychiatrist_id}/notes/{note_id}`: Update or delete a private clinician note.
- `PATCH /api/chat/{telegram_id}/{psychiatrist_id}/{message_id}`: Edit a clinician-authored Telegram message.
- `DELETE /api/chat/{telegram_id}/{psychiatrist_id}/{message_id}?scope=self|everyone`: Hide a clinician message locally or delete it for both chat participants.

Patient assignment is rejected when the psychiatrist has reached their individual capacity. The admin interaction log is aggregate and read-only; admins cannot edit or delete chat messages through this view.

The psychiatrist chat UI places private notes beside the conversation and also offers a Notes action from the patient list. Notes are scoped to the authenticated assigned psychiatrist and are never included in admin endpoints. Telegram bot messages can only be edited/deleted remotely when Telegram permits it (for example, Telegram restricts message deletion by age); legacy messages without a stored Telegram message ID can only be hidden from the clinician's own view. Existing message records are enriched with optional `telegram_message_id`, `edited_at`, `deleted_at`, and `deleted_for_psychiatrist` fields; `backend/patient_notes.json` starts empty to avoid adding fabricated notes to existing patient records.
