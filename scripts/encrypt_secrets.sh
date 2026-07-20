#!/bin/bash
# Path: /mnt/sharedroot/projects/llm-userprofile/scripts/encrypt_secrets.sh

export PATH="$PATH:$HOME/go/bin:$HOME/.local/bin"
AGE_BIN=$(command -v age || echo "/usr/bin/age")

FIDO2_IDENTITY="${AGE_FIDO2_IDENTITY:-$HOME/.config/chezmoi/age-identity.txt}"
RECOVERY_RECIPIENT="${AGE_RECOVERY_RECIPIENT}"

# Sets default target to the main .env, overriding previous unified_secrets.env behavior
TARGET_FILE="${1:-/mnt/sharedroot/projects/llm-userprofile/.env}"
ENCRYPTED_FILE="${TARGET_FILE}.age"

if [ ! -f "$TARGET_FILE" ]; then
    echo "Error: Target file $TARGET_FILE does not exist."
    exit 1
fi

echo "=== STARTING FIDO2 ENCRYPTION ==="
echo "Target: $TARGET_FILE"
echo "Identity: $FIDO2_IDENTITY"

if [ -n "$RECOVERY_RECIPIENT" ]; then
    "$AGE_BIN" -e -i "$FIDO2_IDENTITY" -r "$RECOVERY_RECIPIENT" -o "$ENCRYPTED_FILE" "$TARGET_FILE"
else
    "$AGE_BIN" -e -i "$FIDO2_IDENTITY" -o "$ENCRYPTED_FILE" "$TARGET_FILE"
fi

if [ $? -eq 0 ]; then
    echo "Encryption successful. Output: $ENCRYPTED_FILE"
    echo "Shredding cleartext file..."
    shred -u "$TARGET_FILE" 2>/dev/null || rm -f "$TARGET_FILE"
    echo "=== ENCRYPTION COMPLETE ==="
else
    echo "Error: Encryption failed. Cleartext file was not removed."
    exit 1
fi
