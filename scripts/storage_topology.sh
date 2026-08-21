#!/bin/bash
#
# storage_topology.sh
# Übersicht über Mounts, Devices und Schnittstellen
#

set -euo pipefail

JSON_MODE=0
if [[ "${1:-}" == "--json" ]]; then
    JSON_MODE=1
fi

if [[ "$JSON_MODE" -eq 1 ]]; then
    printf '['
    FIRST=1
fi

if [[ "$JSON_MODE" -eq 0 ]]; then
    printf "\n%-25s %-20s %-8s %-12s %-12s %-15s\n" \
        "MOUNT" "SOURCE" "FSTYPE" "DEVICE" "TRANSPORT" "INFO"

    printf '%*s\n' 100 '' | tr ' ' '-'
fi

findmnt -rn -o TARGET,SOURCE,FSTYPE | while read -r TARGET SOURCE FSTYPE
do
    DEVICE="-"
    TRANSPORT="-"
    INFO="-"

    # Netzwerk-Mounts
    if [[ "$FSTYPE" =~ ^(nfs|nfs4|cifs|smb3|smbfs)$ ]]; then
        INFO="NETWORK"
        if [[ "$JSON_MODE" -eq 1 ]]; then
            [[ "$FIRST" -eq 1 ]] || printf ','
            FIRST=0
            printf '{"mountpoint":"%s","source":"%s","filesystem":"%s","device":"-","transport":"-","info":"%s"}' \
                "${TARGET//\\/\\\\}" "${SOURCE//\\/\\\\}" "$FSTYPE" "$INFO"
        else
            printf "%-25s %-20s %-8s %-12s %-12s %-15s\n" \
                "$TARGET" "$SOURCE" "$FSTYPE" "-" "-" "$INFO"
        fi
        continue
    fi

    # Device bestimmen
    REALDEV=$(readlink -f "$SOURCE" 2>/dev/null || true)

    if [[ -n "$REALDEV" ]]; then

        # RAID erkennen
        if [[ "$REALDEV" =~ ^/dev/md ]]; then
            DEVICE=$(basename "$REALDEV")
            INFO="MD RAID"

            MEMBER=$(lsblk -no PKNAME "$REALDEV" 2>/dev/null | head -1 || true)

            if [ -n "${MEMBER:-}" ]; then
                TRANSPORT=$(lsblk -dn -o TRAN "/dev/$MEMBER" 2>/dev/null || true)
            fi

        # LVM erkennen
        elif lsblk -no TYPE "$REALDEV" 2>/dev/null | grep -q "^lvm$"; then
            DEVICE=$(basename "$REALDEV")
            INFO="LVM"

            PV=$(pvs --noheadings -o pv_name 2>/dev/null | head -1 || true)

            if [ -n "${PV:-}" ]; then
                BASE=$(basename "$PV")
                TRANSPORT=$(lsblk -dn -o TRAN "/dev/$BASE" 2>/dev/null || true)
            fi

        else
            BASE=$(lsblk -ndo PKNAME "$REALDEV" 2>/dev/null || true)

            if [ -z "$BASE" ]; then
                BASE=$(basename "$REALDEV")
            fi

            DEVICE="$BASE"
            TRANSPORT=$(lsblk -dn -o TRAN "/dev/$BASE" 2>/dev/null || true)

            case "$TRANSPORT" in
                sata) INFO="SATA" ;;
                nvme) INFO="NVMe" ;;
                usb)  INFO="USB" ;;
                sas)  INFO="SAS" ;;
                "")   INFO="UNKNOWN" ;;
                *)    INFO="$TRANSPORT" ;;
            esac
        fi
    fi

    if [[ "$JSON_MODE" -eq 1 ]]; then
        [[ "$FIRST" -eq 1 ]] || printf ','
        FIRST=0
        printf '{"mountpoint":"%s","source":"%s","filesystem":"%s","device":"%s","transport":"%s","info":"%s"}' \
            "${TARGET//\\/\\\\}" "${SOURCE//\\/\\\\}" "$FSTYPE" "$DEVICE" "$TRANSPORT" "$INFO"
    else
        printf "%-25s %-20s %-8s %-12s %-12s %-15s\n" \
            "$TARGET" "$SOURCE" "$FSTYPE" "$DEVICE" "$TRANSPORT" "$INFO"
    fi

done

if [[ "$JSON_MODE" -eq 1 ]]; then
    printf ']\n'
    exit 0
fi
