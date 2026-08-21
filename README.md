# Home Dashboard

A small Flask-based home dashboard for bookmarks, devices, and local services.

## Features

- Bookmark management
- Browser bookmark import (HTML/Netscape export and JSON)
- Device discovery and network scanning
- Settings UI and JSON-backed configuration
- Docker-ready packaging

## Run locally

### With Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

Optional: create a local env file first:

```bash
cp docker/.env.example docker/.env
```

Then run with custom values from `docker/.env`.

### Integrate into an existing Docker stack

If you already have multiple containers running in one shared Docker network, connect the dashboard to that network.

1. Check your existing network name:

```bash
docker network ls
```

2. Set the network in `docker/.env`:

```env
DASHBOARD_NETWORK=your-existing-network
```

3. Start the dashboard:

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yml up -d --build
```

The production instance uses `http://localhost:8088`. The Dev Compose setup in this repository uses `http://localhost:8089` and the container name `home-dashboard-dev`.

### Directly with Python

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app is available on <http://localhost:8088>.

## Storage-Übersicht als Skript

Für eine tabellarische Übersicht aller Mounts mit Block-Device und erkannter
Schnittstelle:

```bash
./scripts/storage-report.sh
```

Das Skript nutzt `findmnt`, `df` und optional `lsblk`/`udevadm` und erkennt
unter anderem SATA, NVMe, USB, RAID, LVM, NFS und SMB.

## Project structure

- `backend/` — Flask application and API modules
- `data/` — persisted JSON data files
- `docker/` — Docker configuration

## Notes

This project is intended for local home automation and personal dashboard usage.
