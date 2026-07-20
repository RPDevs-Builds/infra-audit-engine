# Path: src/security.py
import subprocess
from pathlib import Path

def encrypt_environment(env_file: Path):
    """Invokes the existing bash encryption script securely."""
    script_path = Path(__file__).parent.parent / "scripts" / "encrypt_secrets.sh"
    subprocess.run(["bash", str(script_path), str(env_file)], check=True)
    print(f"Encryption sequence triggered for {env_file.name}")
