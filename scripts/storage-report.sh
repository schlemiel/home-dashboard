#!/usr/bin/env bash
set -euo pipefail

print_help() {
  cat <<'EOF'
Nutzung:
  ./scripts/storage-report.sh

Zeigt physische Mounts mit Block-Device, UUID, Dateisystem, Groesse, Belegung und
erkannter Schnittstelle (SATA, NVMe, USB, RAID, LVM, NFS, SMB).
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_help
  exit 0
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Fehler: Benoetigtes Programm fehlt: $1" >&2
    exit 1
  fi
}

require_command findmnt
require_command df

have_lsblk=0
command -v lsblk >/dev/null 2>&1 && have_lsblk=1
have_udevadm=0
command -v udevadm >/dev/null 2>&1 && have_udevadm=1

interface_for() {
  local source="$1"
  local fstype="$2"
  local properties=""
  local transport=""

  case "$fstype" in
    nfs|nfs4) printf 'NFS'; return ;;
    cifs|smb3) printf 'SMB'; return ;;
  esac

  if [[ "$source" == /dev/md* ]]; then
    printf 'RAID'
    return
  fi
  if [[ "$source" == /dev/mapper/* || "$source" == /dev/dm-* ]]; then
    printf 'LVM'
    return
  fi
  if [[ "$source" != /dev/* || "$have_lsblk" -eq 0 ]]; then
    printf 'n/a'
    return
  fi

  transport="$(lsblk -sno TRAN "$source" 2>/dev/null | awk 'NF { value=$1 } END { print value }')"
  case "$transport" in
    sata) printf 'SATA'; return ;;
    nvme) printf 'NVMe'; return ;;
    usb) printf 'USB'; return ;;
  esac

  if [[ "$have_udevadm" -eq 1 ]]; then
    properties="$(udevadm info --query=property --name="$source" 2>/dev/null || true)"
    case "$(printf '%s\n' "$properties" | awk -F= '$1 == "ID_BUS" { print tolower($2); exit }')" in
      ata) printf 'SATA'; return ;;
      nvme) printf 'NVMe'; return ;;
      usb) printf 'USB'; return ;;
    esac
  fi
  printf 'Block-Device'
}

uuid_for() {
  local source="$1"
  local uuid=""

  [[ "$source" == /dev/* ]] || { printf 'n/a'; return; }
  if [[ "$have_lsblk" -eq 1 ]]; then
    uuid="$(lsblk -no UUID "$source" 2>/dev/null | awk 'NF { print; exit }')"
  fi
  if [[ -z "$uuid" && "$have_udevadm" -eq 1 ]]; then
    uuid="$(udevadm info --query=property --name="$source" 2>/dev/null | awk -F= '$1 == "ID_FS_UUID" { print $2; exit }')"
  fi
  printf '%s' "${uuid:-n/a}"
}

device_info_for() {
  local source="$1"
  local info=""

  if [[ "$have_lsblk" -eq 1 ]]; then
    info="$(lsblk -ndo NAME,TYPE,TRAN,SIZE "$source" 2>/dev/null | awk 'NF { print; exit }')"
  fi
  if [[ -n "$info" ]]; then
    read -r device_name device_type device_transport device_size <<< "$info"
  else
    device_name="-"
    device_type="-"
    device_transport="-"
    device_size="-"
  fi
}

is_physical_storage() {
  case "$1" in
    /dev/loop*|/dev/ram*|/dev/zram*) return 1 ;;
    /dev/*) return 0 ;;
    *) return 1 ;;
  esac
}

printf '%-16s %-8s %-8s %-10s %-28s %-24s %-36s %-8s %-12s %-12s %-12s %-14s\n' \
  'NAME' 'TYPE' 'TRAN' 'DEV-SIZE' 'MOUNT' 'SOURCE / DEVICE' 'UUID' 'FSTYPE' 'SIZE' 'USED' 'FREE' 'INTERFACE'
printf '%-16s %-8s %-8s %-10s %-28s %-24s %-36s %-8s %-12s %-12s %-12s %-14s\n' \
  '----------------' '--------' '--------' '----------' '----------------------------' '------------------------' '------------------------------------' '--------' '------------' '------------' '------------' '--------------'

while read -r mountpoint source fstype; do
  [[ -n "$mountpoint" ]] || continue
  is_physical_storage "$source" || continue

  size='-'
  used='-'
  free='-'
  df_values="$(df -P -T -- "$mountpoint" 2>/dev/null | awk 'NR == 2 { print $3 "\t" $4 "\t" $5 "\t" $6 }')"
  if [[ -n "$df_values" ]]; then
    IFS=$'\t' read -r size_kib used_kib free_kib used_percent <<< "$df_values"
    size="${size_kib:-0}K (${used_percent:-0})"
    used="${used_kib:-0}K"
    free="${free_kib:-0}K"
  fi

  device_info_for "$source"
  uuid="$(uuid_for "$source")"
  interface="$(interface_for "$source" "$fstype")"
  printf '%-16s %-8s %-8s %-10s %-28s %-24s %-36s %-8s %-12s %-12s %-12s %-14s\n' \
    "$device_name" "$device_type" "$device_transport" "$device_size" "$mountpoint" "$source" "$uuid" "$fstype" "$size" "$used" "$free" "$interface"
done < <(findmnt -rn -o TARGET,SOURCE,FSTYPE)