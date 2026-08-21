#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$SCRIPT_DIR"

# If executed via sudo, keep ownership for the original invoking user.
EXEC_UID="${SUDO_UID:-$(id -u)}"
EXEC_GID="${SUDO_GID:-$(id -g)}"
EXEC_USER="${SUDO_USER:-$(id -un)}"

SERVICE_NAME="home-dashboard"

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
  - venv/                   (Python-Virtualenv mit Flask + Gunicorn)
  - home-dashboard.service  (systemd-Unit-Datei)

Berechtigungen:
  - Zielordner-Inhalte gehören dem ausführenden User

Wird das Skript als root (sudo) ausgeführt, installiert es die systemd-Unit
zusätzlich nach /etc/systemd/system/ und startet den Dienst direkt.
Ohne root-Rechte wird die Unit-Datei nur im Zielordner erzeugt; die
Installation kann dann manuell erfolgen (siehe Ausgabe am Ende).
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

echo "[2/5] Erzeuge Python-Virtualenv und installiere Abhängigkeiten"
python3 -m venv "$TARGET_DIR/venv"
"$TARGET_DIR/venv/bin/pip" install --upgrade pip >/dev/null
"$TARGET_DIR/venv/bin/pip" install -r "$TARGET_DIR/backend/requirements.txt"

echo "[3/5] Erzeuge systemd-Unit-Datei"
cat > "$TARGET_DIR/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Home Dashboard (Flask/Gunicorn)
After=network.target

[Service]
Type=simple
User=${EXEC_USER}
Group=${EXEC_USER}
WorkingDirectory=${TARGET_DIR}/backend
Environment=PATH=${TARGET_DIR}/venv/bin
ExecStart=${TARGET_DIR}/venv/bin/gunicorn -c gunicorn.conf.py app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[4/5] Setze Besitzrechte"
chown -R "${EXEC_UID}:${EXEC_GID}" "$TARGET_DIR"
# venv/ enthält ausführbare Skripte/Symlinks; von der generischen chmod-Runde ausnehmen.
find "$TARGET_DIR" -path "$TARGET_DIR/venv" -prune -o -type d -exec chmod 755 {} \;
find "$TARGET_DIR" -path "$TARGET_DIR/venv" -prune -o -type f -exec chmod 644 {} \;
chmod +x "$TARGET_DIR/scripts/storage-report.sh"
chmod +x "$TARGET_DIR/scripts/storage_topology.sh"
chmod +x "$TARGET_DIR/venv/bin/gunicorn"

echo "[5/5] systemd-Dienst"
if [[ "$(id -u)" -eq 0 ]]; then
  cp "$TARGET_DIR/${SERVICE_NAME}.service" "/etc/systemd/system/${SERVICE_NAME}.service"
  systemctl daemon-reload
  systemctl enable --now "${SERVICE_NAME}.service"
  echo "      Dienst installiert und gestartet: systemctl status ${SERVICE_NAME}"
else
  echo "      Kein root: Unit-Datei wurde nur unter $TARGET_DIR/${SERVICE_NAME}.service erzeugt."
  echo "      Manuell installieren mit:"
  echo "        sudo cp \"$TARGET_DIR/${SERVICE_NAME}.service\" /etc/systemd/system/${SERVICE_NAME}.service"
  echo "        sudo systemctl daemon-reload"
  echo "        sudo systemctl enable --now ${SERVICE_NAME}.service"
fi

echo
echo "Setup abgeschlossen."
echo "Zielordner: $TARGET_DIR"
echo "Owner: ${EXEC_USER} (${EXEC_UID}:${EXEC_GID})"
