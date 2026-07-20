# Path: /mnt/sharedroot/projects/llm-userprofile/AUDIT/src/enroll.py

import os
import re
import getpass
from pathlib import Path

# Resolve .env path relative to this script
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

def get_next_index() -> int:
    """Scans the .env file to find the highest host index currently in use."""
    if not ENV_FILE.exists():
        return 1
    
    max_idx = 0
    with open(ENV_FILE, "r") as f:
        for line in f:
            match = re.match(r"^host(\d+)=", line)
            if match:
                idx = int(match.group(1))
                if idx > max_idx:
                    max_idx = idx
    return max_idx + 1

def main():
    print("\n=== INFRASTRUCTURE AUDIT ENROLLMENT ===")
    
    target_type = input("Target Type (ssh / github / cloudflare) [ssh]: ").strip().lower() or "ssh"
    name = input("Target Name (e.g., prod-db-01): ").strip()
    
    if not name:
        print("Error: Target name cannot be empty.")
        return

    # Determine required fields based on integration type
    if target_type == "ssh":
        address = input("IP Address / Hostname: ").strip()
        user = input("SSH Username [root]: ").strip() or "root"
        password = getpass.getpass("SSH Password / Key Path (Hidden): ").strip()
        audit = "system,docker,network"
        
    elif target_type == "github":
        address = "api.github.com"
        user = input("GitHub Organization / Username: ").strip()
        password = getpass.getpass("GitHub PAT (Hidden): ").strip()
        audit = "repositories,runners,billing"
        
    elif target_type == "cloudflare":
        address = "api.cloudflare.com"
        user = input("Cloudflare Account ID: ").strip()
        password = getpass.getpass("Cloudflare API Token (Hidden): ").strip()
        audit = "zones,tunnels,workers"
        
    else:
        print(f"Error: Unknown target type '{target_type}'.")
        return

    idx = get_next_index()
    
    env_block = f"""
# Target {idx}: {name} ({target_type.upper()})
host{idx}={address}
host{idx}name={name}
host{idx}user={user}
host{idx}pass={password}
host{idx}audit={audit}
"""
    
    # Append the new configuration block
    with open(ENV_FILE, "a") as f:
        f.write(env_block)
        
    print(f"\n[+] Successfully enrolled '{name}' as host{idx} in .env")
    print("[!] NOTE: If you are utilizing Age/FIDO2 hardware encryption, remember to run your encrypt_secrets.sh routine to secure the updated file.")

if __name__ == "__main__":
    main()
