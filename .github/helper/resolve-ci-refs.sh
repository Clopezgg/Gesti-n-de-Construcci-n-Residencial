#!/usr/bin/env bash
set -euo pipefail

resolve_frappe_ref() {
    local repository_ref="${1:-}"
    if [[ -n "${FRAPPE_BRANCH:-}" ]]; then
        printf '%s\n' "$FRAPPE_BRANCH"
        return
    fi

    case "$repository_ref" in
        main|reconstruccion-definitiva-construcontrol|consolidation/*|"")
            printf '%s\n' "${CONSTRUCONTROL_FRAPPE_REF:-v15.115.4}"
            ;;
        *)
            printf '%s\n' "$repository_ref"
            ;;
    esac
}

resolve_payments_ref() {
    printf '%s\n' "${PAYMENTS_BRANCH:-version-15}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    resolve_frappe_ref "${1:-}"
    resolve_payments_ref
fi
