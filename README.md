# Secure Remote System Diagnostic System

A consent-first diagnostic sharing prototype with:

- `desktop-client/` - cross-platform Python Tkinter app for PIN entry, scan consent, progress, and upload.
- `backend/` - FastAPI API for checker auth, PIN sessions, report upload, and session results.
- `web-dashboard/` - React dashboard for reviewers to generate PINs and inspect completed reports.

This is a local development scaffold. It intentionally favors transparency and narrow data collection over deep system inspection.

## Quick Start

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python server.py
```

Default checker login:

- Email: `checker@example.com`
- Password: `change-me`

Set `CHECKER_EMAIL`, `CHECKER_PASSWORD`, and `API_TOKEN_SECRET` in the environment for non-demo use.

### Web Dashboard

```powershell
cd web-dashboard
npm install
npm run dev
```

Open `http://localhost:3000`.

For Netlify, deploy the `web-dashboard` folder with:

- Build command: `npm run build`
- Publish directory: `dist`
- Environment variable: `VITE_API_URL=https://your-public-backend-url`
- Optional: `VITE_SCANNER_DOWNLOAD_URL=https://github.com/popesmoke/test/releases/download/scanner-latest/dngscanner.exe`
- Optional: `VITE_PUBLIC_APP_URL=https://your-dashboard-url` (used in invite links)

When a reviewer generates a PIN, the API returns `download_url` and `invite_url` fields. Share the invite link (`/?pin=123456`) with suspects so they can download the scanner and see their PIN without logging in.

Backend download settings:

- `SCANNER_DOWNLOAD_URL` — redirect `/download/scanner` to a hosted EXE (GitHub release recommended)
- `PUBLIC_APP_URL` — dashboard origin for invite links
- `PUBLIC_API_URL` — API origin when building default download URLs

The dashboard is static. The backend must be hosted separately on a service that can run a Python web server, such as a VPS, Render, Railway, Fly.io, or another server host.

### Desktop Client

```powershell
cd desktop-client
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The client uploads to `http://localhost:8000` by default. Change `DIAGNOSTIC_API_URL` if needed.

To build a Windows EXE:

```powershell
.\build-desktop-exe.bat
```

The EXE is created at `desktop-client\dist\SecureRemoteDiagnostic.exe`.

## Privacy Model

The desktop client:

- Shows what categories are collected before scanning.
- Waits for an explicit user action before scanning.
- Collects a system overview, resource summary, process names/counts, installed app summary where available, and approved application logs only.
- Hashes device identifiers locally before upload.
- Does not run hidden background monitoring.

## Implementation Note

The backend is currently a dependency-free Python HTTP server to avoid native package build failures on newer Python versions. It exposes the same local API used by the dashboard and desktop client.

## Production Hardening Checklist

- Put the API behind HTTPS.
- Replace demo auth with a real identity provider or hardened password auth.
- Store password hashes with a managed user table.
- Use PostgreSQL or MongoDB instead of local SQLite.
- Add rate limiting for login, PIN creation, and report upload.
- Encrypt reports at rest.
- Add an audit log for all checker access.
- Add granular user consent toggles for optional scan categories.
- Sign and notarize desktop builds.
