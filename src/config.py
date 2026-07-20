# Path: /mnt/sharedroot/projects/llm-userprofile/AUDIT/src/config.py

import os
import subprocess
import tempfile
import sys
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
    If found, enforces FIDO2 decryption to a RAM disk, loads secrets into memory, 
    and aggressively shreds the temporary file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if ENV_AGE.exists():
        print("=== DECRYPTING ENVIRONMENT SECRETS ===")
        secure_mem = Path("/dev/shm") if Path("/dev/shm").is_dir() else Path("/tmp")
        fd, temp_path = tempfile.mkstemp(dir=secure_mem, prefix="env_")
        os.close(fd)
        temp_file = Path(temp_path)

        try:
            result = subprocess.run(
                ["age", "-d", "-i", FIDO2_IDENTITY, "-o", str(temp_file), str(ENV_AGE)],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                load_dotenv(dotenv_path=temp_file)
            else:
                print(f"Error: Decryption failed or FIDO2 touch timed out.\n{result.stderr}")
                raise RuntimeError("FIDO2 Hardware Decryption Failed")
                
        finally:
            if temp_file.exists():
                subprocess.run(["shred", "-u", str(temp_file)], check=False)
                if temp_file.exists():
                    temp_file.unlink()

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
