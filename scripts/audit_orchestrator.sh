#!/bin/bash
# Path: ./scripts/audit_orchestrator.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

ENV_FILE="$PROJECT_ROOT/.env"
ENV_AGE="${ENV_FILE}.age"
FIDO2_IDENTITY="${AGE_FIDO2_IDENTITY:-$HOME/.config/chezmoi/age-identity.txt}"
AGE_BIN=$(command -v age || echo "/usr/bin/age")

# Secure Environment Loading
if [ -f "$ENV_AGE" ]; then
    echo "=== DECRYPTING ENVIRONMENT SECRETS ==="
    echo "Waiting for FIDO2 hardware touch..."
    SECURE_MEM="/dev/shm"
    [ -d "$SECURE_MEM" ] || SECURE_MEM="/tmp"
    SECURE_TMP=$(mktemp "$SECURE_MEM/env_XXXXXX")
    trap 'rm -f "$SECURE_TMP"' EXIT INT TERM
    
    "$AGE_BIN" -d -i "$FIDO2_IDENTITY" -o "$SECURE_TMP" "$ENV_AGE"
    if [ $? -eq 0 ]; then
        source "$SECURE_TMP"
        rm -f "$SECURE_TMP"
        echo "Decryption successful. Secrets loaded into memory."
    else
        echo "Error: Decryption failed or FIDO2 touch timed out."
        rm -f "$SECURE_TMP"
        exit 1
    fi
elif [ -f "$ENV_FILE" ]; then
    echo "WARNING: Using cleartext .env file. Consider encrypting via encrypt_secrets.sh."
    source "$ENV_FILE"
else
    echo "Error: Neither $ENV_AGE nor $ENV_FILE found in $PROJECT_ROOT."
    exit 1
fi

export OUTPUT_DIR="$PROJECT_ROOT/docs/audit_output"
mkdir -p "$OUTPUT_DIR"

# Source external modules
source "$SCRIPT_DIR/infrastructure_audit.sh"
source "$SCRIPT_DIR/github_audit.sh"
source "$SCRIPT_DIR/cloudflare_audit.sh"

# ---------------------------------------------------------
# EXECUTION ROUTING
# ---------------------------------------------------------
for i in {1..6}; do
    name_var="host${i}name"
    ip_var="host${i}"
    user_var="host${i}user"
    pass_var="host${i}pass"
    audit_var="host${i}audit"

    if [ -n "${!ip_var}" ]; then
        if [[ "${!name_var}" == "github" ]]; then
            run_github_audit "${!ip_var}" "${!pass_var}" "${!audit_var}" "$OUTPUT_DIR"
        elif [[ "${!name_var}" == "cloudflare" ]]; then
            run_cloudflare_audit "${!user_var}" "${!pass_var}" "${!audit_var}" "$OUTPUT_DIR"
        else
            run_infrastructure_audit "${!ip_var}" "${!user_var}" "${!pass_var}" "${!audit_var}" "${!name_var}" "$OUTPUT_DIR"
        fi
    fi
done

echo "=== AUDIT COMPLETE: Files saved to $OUTPUT_DIR/ ==="
echo "=== INITIATING REGISTRY MERGE ==="
bash "$PROJECT_ROOT/scripts/update_registry.sh"
