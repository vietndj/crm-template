# CRM Template

A lightweight CRM system for small businesses, deployed free on Cloudflare Pages and D1 (SQLite).

## Features
- Mobile-first UI using Alpine.js and Tailwind CSS (no build step)
- Master password authentication
- Manage Leads, Contacts, Pipeline, Products
- Interactions history (Calls, Notes)
- Import from CSV
- Cloudflare Pages Functions Backend (JS/ESM)
- D1 SQLite Database

## Quick Start

**Mac / Linux:**
```bash
./setup.sh
```

**Windows:**
```cmd
setup.bat
```
*(One-command deployment script to install dependencies, setup DB, and deploy to Cloudflare Pages)*

## API Documentation
All endpoints require `Authorization: Bearer <token>` header.

- `GET /api/leads` - List leads (query: search, limit, offset)
- `POST /api/leads` - Create lead
- `GET /api/leads/:id` - Get lead
- `PUT /api/leads/:id` - Update lead
- `DELETE /api/leads/:id` - Delete lead
- `GET /api/interactions?lead_id=:id` - Get interactions
- `POST /api/interactions` - Add interaction
- `GET /api/products` - List products
- `POST /api/auth/login` - Login

## Platform Sync Guides

We provide sync scripts in the `sync/` directory:

### macOS Contacts & Calls
1. **Sync Contacts:** Pushes CRM leads to macOS Contacts app.
   ```bash
   python3 sync/mac/sync_contacts.py --api-url https://YOUR-APP.pages.dev --token YOUR_TOKEN
   ```
2. **Sync Calls:** Reads macOS Call History and logs calls to CRM interactions.
   ```bash
   python3 sync/mac/sync_calls.py --api-url https://YOUR-APP.pages.dev --token YOUR_TOKEN
   ```

### Windows & Telegram
- **Sync Telegram:** Run a Telegram bot that interfaces with your CRM for notifications and quick actions.
   ```bash
   python3 sync/win/sync_telegram.py --api-url https://YOUR-APP.pages.dev --token YOUR_TOKEN --bot-token YOUR_BOT_TOKEN
   ```

## FAQ
- **How do I login?** Use the master password set during the setup script.
- **Is it really free?** Cloudflare offers generous free tiers for Pages and D1, typically more than enough for a small business.
