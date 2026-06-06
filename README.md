# Virello Scanner

A consent-first diagnostic sharing system with:

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

For production, set `DATABASE_URL` to a PostgreSQL connection string. If `DATABASE_URL` is not set, the backend falls back to the local SQLite file at `backend/diagnostics.db`.

### Discord role-gated dashboard login

The dashboard supports normal email/password accounts, but the backend only issues a usable dashboard token after the user verifies through Discord and belongs to your configured Discord server with the configured `Access` role. Discord is checked each time a normal user signs in.

Create an app in the Discord Developer Portal, then add this redirect URL to the app's OAuth2 redirects:

```text
https://virello-secure.onrender.com/auth/discord/callback
```

Set these backend environment variables:

```text
DATABASE_URL=your Render PostgreSQL internal database URL
DISCORD_CLIENT_ID=1510615702103392327
DISCORD_CLIENT_SECRET=your Discord application client secret
DISCORD_REDIRECT_URI=https://virello-secure.onrender.com/auth/discord/callback
DISCORD_GUILD_ID=1510614253508493373
DISCORD_ACCESS_ROLE_ID=1510614274299531334
FRONTEND_URL=https://virello-secure.pages.dev
CORS_ORIGINS=http://localhost:3000,https://virello-secure.pages.dev
API_TOKEN_SECRET=a long random secret
```

The Discord OAuth scopes used are `identify` and `guilds.members.read`.

The public Discord invite shown on the login page defaults to `https://discord.gg/wPZXKaPyWY`.

### Automated database backup and recovery

The backend can export the full database every 29 days and upload the backup to a Discord channel using a bot token. On startup, if the database is empty (for example after a Render PostgreSQL reset), the backend automatically downloads the latest Discord backup and restores all tables.

Create a Discord bot in the Developer Portal, invite it to your server, and grant it permission to **Send Messages**, **Attach Files**, and **Read Message History** in the backup channel.

Set these backend environment variables on Render:

```text
DISCORD_BOT_TOKEN=your Discord bot token
DISCORD_BACKUP_CHANNEL_ID=your backup channel ID
BACKUP_INTERVAL_DAYS=29
BACKUP_AUTO_RESTORE=true
BACKUP_ENABLED=true
```

Optional tuning:

```text
BACKUP_CHECK_INTERVAL_SECONDS=3600
BACKUP_AUTO_RESTORE=false
```

Backups are stored as gzip-compressed JSON attachments named `virello-db-backup-<timestamp>.json.gz` in the configured channel.

### Health check and UptimeRobot

The backend exposes `GET /health` for uptime monitoring. A healthy response returns HTTP 200 with `"status": "ok"` and includes database and backup metadata.

Example production monitor URL:

```text
https://virello-secure.onrender.com/health
```

In UptimeRobot, create an HTTP(s) monitor with a 5-minute interval and set the keyword monitor to `ok` so failed database connectivity returns HTTP 503 and triggers an alert.

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

The EXE is created at `desktop-client\dist-secure\virello-scanner.exe`.

## Privacy Model

The desktop client:

- Shows what categories are collected before scanning.
- Waits for an explicit user action before scanning.
- Collects a system overview, resource summary, process names/counts, installed app summary where available, and approved application logs only.
- Hashes device identifiers locally before upload.
- Does not run hidden background monitoring.

## Implementation Note

The backend uses PostgreSQL when `DATABASE_URL` is configured and SQLite as a local development fallback. It exposes the same API used by the dashboard and desktop client.

## Production Hardening Checklist

- Put the API behind HTTPS.
- Replace demo auth with a real identity provider or hardened password auth.
- Store password hashes with a managed user table.
- Add rate limiting for login, PIN creation, and report upload.
- Encrypt reports at rest.
- Add an audit log for all checker access.
- Add granular user consent toggles for optional scan categories.
- Sign and notarize desktop builds.
