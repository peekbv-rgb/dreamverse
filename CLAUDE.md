# Nieuwe app

**Placeholder name and placeholder purpose — fill both in before anything is
built on top of this.** Scaffolded 1 September 2026 as a clean project, not
related to the Cat or Pia avatars and sharing no code with them.

Shared company context is inherited from `AI/CLAUDE.md`, so it is not repeated
here. This file carries only what is specific to this project.

## What it is

_One or two sentences: who uses it, what it does for them, which company (if
any) it serves._

## Stack

Python 3.14, standard-library `http.server`, static frontend, deployed to
Render. No web framework — the other projects here run this way and it keeps the
deploy to one file. Reach for FastAPI or Flask the day routing, validation or
async actually calls for it.

| Piece | Where |
|---|---|
| Server and API | `server.py` |
| Frontend | `static/` |
| Secrets (git-ignored) | `.env`, template in `.env.example` |
| Deploy definition | `render.yaml` |

## Run it

```bash
pip install -r requirements.txt
python server.py
```

Then open `http://127.0.0.1:8000`. `/api/health` returns `{"ok": true}` and is
what the page checks on load.

## Rules that already apply

- **Never commit `.env`.** `.gitignore` also blocks `.env.*` and `*.env.*`,
  because a backup named `.env.bak-nfd` once slipped past narrower patterns in
  a sibling project and reached GitHub.
- Basic auth switches on as soon as `AUTH_USER` and `AUTH_PASSWORD` are both
  set, and is off while either is blank. Give this project its own credentials;
  do not copy another project's `.env`.
- On Render, `HOST` must be `0.0.0.0` — `render.yaml` sets it. Locally leave it
  on `127.0.0.1` so the app is not exposed to the LAN.

## Open questions

- What is this app for, and what is its real name?
- Does it need a database? Nothing here persists anything yet.
