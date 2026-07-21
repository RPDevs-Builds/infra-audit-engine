# Path: /mnt/sharedroot/projects/infra-audit-engine/src/registry.py

import os
import shutil
from datetime import datetime
from pathlib import Path
from ruamel.yaml import YAML
from typing import Any, Dict

class RegistryManager:
    def __init__(self, registry_path: str):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.path = Path(registry_path)
        self.history_dir = self.path.parent / "history"
        self.history_dir.mkdir(exist_ok=True)
        self.history_limit = int(os.getenv("AUDIT_HISTORY_LIMIT", "5"))

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"environment_registry": {"nodes": {}, "github_ecosystem": {}, "cloud_infrastructure": {}}}
        with open(self.path, 'r') as f:
            return self.yaml.load(f)

    def normalize_keys(self, data: Dict[str, Any]):
        if "environment_registry" in data:
            ecosystem = data["environment_registry"].get("github_ecosystem", {})
            keys_to_del = [k for k in ecosystem.keys() if k != k.lower() or "_" in k]
            for k in keys_to_del:
                del ecosystem[k]

    def save(self, data: Dict[str, Any]):
        self.normalize_keys(data)
        self.archive_registry()
        self.cleanup_history()
        with open(self.path, 'w') as f:
            self.yaml.dump(data, f)

    def archive_registry(self):
        if self.path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy(self.path, self.history_dir / f"registry_{timestamp}.yml")

    def cleanup_history(self):
        files = sorted(self.history_dir.glob("registry_*.yml"), key=os.path.getmtime, reverse=True)
        for f in files[self.history_limit:]:
            f.unlink()

    def get_previous_registry(self) -> Dict[str, Any]:
        files = sorted(self.history_dir.glob("registry_*.yml"), key=os.path.getmtime, reverse=True)
        if not files: return {}
        with open(files[0], 'r') as f: return self.yaml.load(f)

    def update_node_audit(self, reg_data: Dict, name: str, audit_data: Dict):
        if "nodes" not in reg_data["environment_registry"]: reg_data["environment_registry"]["nodes"] = {}
        if name not in reg_data["environment_registry"]["nodes"]: reg_data["environment_registry"]["nodes"][name] = {"name": name}
        reg_data["environment_registry"]["nodes"][name]["latest_audit"] = audit_data

    def update_github_ecosystem(self, reg_data: Dict, identifier: str, audit_data: Dict):
        if "github_ecosystem" not in reg_data["environment_registry"]: reg_data["environment_registry"]["github_ecosystem"] = {}
        reg_data["environment_registry"]["github_ecosystem"][identifier.lower()] = audit_data
