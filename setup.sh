#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$SCRIPT_DIR"

# If executed via sudo, keep ownership for the original invoking user.
EXEC_UID="${SUDO_UID:-$(id -u)}"
EXEC_GID="${SUDO_GID:-$(id -g)}"
EXEC_USER="${SUDO_USER:-$(id -un)}"

print_help() {
  cat <<'EOF'
Nutzung:
  ./setup.sh /pfad/zum/zielordner

Optional:
  ./setup.sh               # fragt interaktiv nach dem Zielordner
  ./setup.sh -h|--help     # zeigt diese Hilfe

Was erstellt wird:
  - backend/                (Flask-App)
  - data/                   (persistente JSON-Daten; vorhandene Daten bleiben erhalten)
  - scripts/                (Storage-Übersicht)
  - Dockerfile
  - docker-compose.yml
  - .env

Berechtigungen:
  - Zielordner-Inhalte gehören dem ausführenden User
  - Docker nutzt dessen UID/GID für Schreibzugriffe in Volumes

Danach kann im Zielordner direkt gestartet werden mit:
  docker compose up -d --build
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_help
  exit 0
fi

TARGET_INPUT="${1:-}"
if [[ -z "$TARGET_INPUT" ]]; then
  read -r -p "Zielordner (absolut oder relativ): " TARGET_INPUT
fi

if [[ -z "$TARGET_INPUT" ]]; then
  echo "Fehler: Kein Zielordner angegeben."
  exit 1
fi

if [[ "$TARGET_INPUT" = /* ]]; then
  TARGET_DIR="$TARGET_INPUT"
else
  TARGET_DIR="$PWD/$TARGET_INPUT"
fi

mkdir -p "$TARGET_DIR"

echo "[1/5] Kopiere App-Dateien nach: $TARGET_DIR"
mkdir -p "$TARGET_DIR/backend" "$TARGET_DIR/data" "$TARGET_DIR/scripts"
cp -a "$SOURCE_ROOT/backend/." "$TARGET_DIR/backend/"
if find "$TARGET_DIR/data" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  echo "      Produktionsdaten vorhanden; data/ wird nicht überschrieben."
else
  cp -a "$SOURCE_ROOT/data/." "$TARGET_DIR/data/"
fi
cp -a "$SOURCE_ROOT/scripts/." "$TARGET_DIR/scripts/"

echo "[2/5] Erzeuge Dockerfile"
cat > "$TARGET_DIR/Dockerfile" <<'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY backend /app/backend
COPY data /app/data
COPY scripts /app/scripts

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    iputils-ping \
    net-tools \
  nmap \
  util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

EXPOSE 8088

CMD ["python", "/app/backend/app.py"]
EOF

echo "[3/5] Erzeuge docker-compose.yml"
cat > "$TARGET_DIR/docker-compose.yml" <<'EOF'
services:
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ${DASHBOARD_CONTAINER_NAME:-home-dashboard}
    user: "${PUID:-1000}:${PGID:-1000}"
    environment:
      - TZ=${TZ:-Europe/Berlin}
    ports:
      - "${DASHBOARD_PORT:-8088}:8088"
    volumes:
      - ./data:/app/data
      - ./backend/config:/app/backend/config
    cap_add:
      - NET_ADMIN
      - NET_RAW
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8088/api/health', timeout=2).status==200 else 1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    networks:
      - dashboard-net
    restart: unless-stopped

networks:
  dashboard-net:
    name: ${DASHBOARD_NETWORK:-home-dashboard-net}
EOF

echo "[4/5] Erzeuge .env"
cat > "$TARGET_DIR/.env" <<'EOF'
DASHBOARD_PORT=8088
DASHBOARD_CONTAINER_NAME=home-dashboard
DASHBOARD_NETWORK=home-dashboard-net
TZ=Europe/Berlin
PUID=__PUID__
PGID=__PGID__
EOF

sed -i "s/__PUID__/${EXEC_UID}/" "$TARGET_DIR/.env"
sed -i "s/__PGID__/${EXEC_GID}/" "$TARGET_DIR/.env"

# Ensure predictable host-side permissions in the generated setup.
chown -R "${EXEC_UID}:${EXEC_GID}" "$TARGET_DIR"
find "$TARGET_DIR" -type d -exec chmod 755 {} \;
find "$TARGET_DIR" -type f -exec chmod 644 {} \;
chmod +x "$TARGET_DIR/scripts/storage-report.sh"
chmod +x "$TARGET_DIR/scripts/storage_topology.sh"

echo "[5/5] Fertig"
echo
echo "Setup abgeschlossen."
echo "Zielordner: $TARGET_DIR"
echo "Owner: ${EXEC_USER} (${EXEC_UID}:${EXEC_GID})"
echo "Starten mit:"
echo "  cd \"$TARGET_DIR\""
echo "  docker compose up -d --build"
