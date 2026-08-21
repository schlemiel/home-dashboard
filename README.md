# Home Dashboard

A small Flask-based home dashboard for bookmarks, devices, and local services.

## Features

- Bookmark management
- Browser bookmark import (HTML/Netscape export and JSON)
- Device discovery and network scanning
- Settings UI and JSON-backed configuration
- Production deployment via Gunicorn + systemd

## Run locally

### Directly with Python (development)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app is available on <http://localhost:8088>.

### Production deployment (Gunicorn + systemd)

Use `setup.sh` to deploy the app into a production folder with its own
virtualenv, Gunicorn, and a systemd unit:

```bash
./setup.sh /opt/home-dashboard
```

This creates in the target folder:

- `backend/`, `data/`, `scripts/` — application files (existing `data/` is preserved)
- `venv/` — Python virtualenv with Flask and Gunicorn installed
- `home-dashboard.service` — systemd unit running `gunicorn -c gunicorn.conf.py app:app`

If run as root (e.g. via `sudo ./setup.sh ...`), the unit is installed to
`/etc/systemd/system/` and started automatically. Otherwise, install it manually:

```bash
sudo cp /opt/home-dashboard/home-dashboard.service /etc/systemd/system/home-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now home-dashboard.service
```

Check status and logs:

```bash
systemctl status home-dashboard
journalctl -u home-dashboard -f
```

The Gunicorn bind port is read from `backend/config/settings.json`
(`dashboard.port`, default `8088`).

## Storage-Übersicht als Skript

Für eine tabellarische Übersicht aller Mounts mit Block-Device und erkannter
Schnittstelle:

```bash
./scripts/storage-report.sh
```

Das Skript nutzt `findmnt`, `df` und optional `lsblk`/`udevadm` und erkennt
unter anderem SATA, NVMe, USB, RAID, LVM, NFS und SMB.

## Project structure

- `backend/` — Flask application, API modules, and Gunicorn config
- `data/` — persisted JSON data files
- `setup.sh` — deploys the app to a production folder with venv + systemd

## Notes

This project is intended for local home automation and personal dashboard usage.
