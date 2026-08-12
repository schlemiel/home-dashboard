# Home Dashboard

A small Flask-based home dashboard for bookmarks, devices, and local services.

## Features

- Bookmark management
- Device discovery and network scanning
- Settings UI and JSON-backed configuration
- Docker-ready packaging

## Run locally

### With Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

### Directly with Python

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app is available on http://localhost:8088.

## Project structure

- `backend/` — Flask application and API modules
- `data/` — persisted JSON data files
- `docker/` — Docker configuration

## Notes

This project is intended for local home automation and personal dashboard usage.
