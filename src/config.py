# Path: /mnt/sharedroot/projects/llm-userprofile/AUDIT/src/config.py

import os
import subprocess
import sys
import io
from pathlib import Path
from dotenv import load_dotenv

def get_base_path():
    """Resolves correct path whether running as a Python script or PyInstaller binary."""
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable))
    return Path(os.path.dirname(os.path.abspath(__file__))).parent

# Resolve project boundaries
PROJECT_ROOT = get_base_path()
ENV_FILE = PROJECT_ROOT / ".env"
ENV_AGE = PROJECT_ROOT / ".env.age"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "audit_output"

# Hardware Trust Variables
FIDO2_IDENTITY = os.getenv("AGE_FIDO2_IDENTITY", str(Path.home() / ".config" / "chezmoi" / "age-identity.txt"))

def load_environment() -> None:
    """
    Evaluates the presence of Age-encrypted environment variables.
    If found, enforces FIDO2 decryption directly into memory via stdout,
    eliminating virtual file system writes and race conditions.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if ENV_AGE.exists():
        print("=== DECRYPTING ENVIRONMENT SECRETS ===")
        try:
            result = subprocess.run(
                ["age", "-d", "-i", FIDO2_IDENTITY, str(ENV_AGE)],
                capture_output=True,
                text=True,
                check=True
            )
            load_dotenv(stream=io.StringIO(result.stdout))
        except subprocess.CalledProcessError as e:
            print(f"Error: Decryption failed or FIDO2 touch timed out.\n{e.stderr}")
            raise RuntimeError("FIDO2 Hardware Decryption Failed")

    elif ENV_FILE.exists():
        print("WARNING: Using cleartext .env file. Consider encrypting via encrypt_secrets.sh.")
        load_dotenv(dotenv_path=ENV_FILE)
    else:
        raise FileNotFoundError(f"Neither {ENV_AGE} nor {ENV_FILE} found in {PROJECT_ROOT}.")

def get_hosts_from_env() -> list[dict]:
    """
    Parses the loaded environment variables to extract dynamically defined audit hosts.
    Returns a list of configuration dictionaries mapping to the execution routing.
    """
    hosts = []
    for i in range(1, 10):  # Expanded index tolerance for scaling
        ip_val = os.getenv(f"host{i}")
        if not ip_val:
            continue
            
        hosts.append({
            "id": i,
            "name": os.getenv(f"host{i}name", "unknown"),
            "address": ip_val,
            "user": os.getenv(f"host{i}user", ""),
            "password": os.getenv(f"host{i}pass", ""),
            "audit_scope": os.getenv(f"host{i}audit", "").split(",")
        })
    return hosts
