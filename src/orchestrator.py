# Path: src/orchestrator.py

import asyncio
import logging
from datetime import datetime
from config import load_environment, get_hosts_from_env, PROJECT_ROOT
from logger import setup_system_logger

# Initialize logging BEFORE modules run to enforce third-party silencing
logger = setup_system_logger(PROJECT_ROOT)

from modules.github_api import GitHubAuditor
from modules.cloudflare_api import CloudflareAuditor
from modules.ssh_audit import InfrastructureAuditor
from registry import RegistryManager

def dict_diff(old, new, path=""):
    """Recursively compares dicts, formatting large outputs to prevent terminal noise."""
    ignore_keys = {'collected_at', 'load_average', 'memory_active', 'ssh_keys_verified'}
    diffs = []
    if not old: return diffs
    
    reg_old = old.get("environment_registry", {})
    reg_new = new.get("environment_registry", {})
    
    def format_val(v):
        """Summarizes large structures and truncates strings for clean logging."""
        if isinstance(v, dict):
            return f"[Dictionary: {len(v)} keys]"
        elif isinstance(v, list):
            return f"[List: {len(v)} items]"
        
        v_str = str(v)
        return v_str if len(v_str) < 60 else v_str[:57] + "..."
    
    def recursive_compare(o_data, n_data, current_path):
        keys = set(list(o_data.keys()) + list(n_data.keys()))
        for k in keys:
            if k in ignore_keys: continue
            
            p = f"{current_path}.{k}" if current_path else k
            o_val = o_data.get(k)
            n_val = n_data.get(k)
            
            if k not in o_data:
                diffs.append(f"ADDED: {p} | VALUE: {format_val(n_val)}")
            elif k not in n_data:
                diffs.append(f"REMOVED: {p} | OLD VALUE: {format_val(o_val)}")
            elif o_val != n_val:
                if isinstance(o_val, dict) and isinstance(n_val, dict):
                    recursive_compare(o_val, n_val, p)
                else:
                    diffs.append(f"CHANGED: {p} | OLD: {format_val(o_val)} | NEW: {format_val(n_val)}")

    recursive_compare(reg_old, reg_new, "")
    return diffs

async def run_audit_task(host):
    """Execution wrapper for individual infrastructure nodes."""
    try:
        if host['name'] == "github":
            auditor = GitHubAuditor(host['user'], host['password'])
            result = await auditor.audit()
            return (host['name'], host['user'], result)
        elif host['name'] == "cloudflare":
            auditor = CloudflareAuditor(host['user'], host['password'], host['audit_scope'], "")
            result = await auditor.audit()
            return (host['name'], host['name'], result)
        else:
            auditor = InfrastructureAuditor(host['address'], host['user'], host['password'])
            result = await auditor.get_system_stats(host['name'])
            return (host['name'], host['name'], result)
    except Exception as e:
        logger.error(f"Critical failure in module {host.get('name', 'unknown')}: {e}")
        return (host.get('name', 'unknown'), host.get('address'), e)

async def main():
    logger.info("Initializing Infrastructure Audit Engine...")
    load_environment()
    hosts = get_hosts_from_env()
    
    registry = RegistryManager(str(PROJECT_ROOT / "docs" / "CURRENT_ENV.yml"))
    reg_data = registry.load()
    prev_reg = registry.get_previous_registry()

    # Launch audit tasks concurrently
    logger.info(f"Dispatching audit tasks for {len(hosts)} target(s)...")
    tasks = [run_audit_task(host) for host in hosts]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception): continue

        name, identifier, audit_result = result
        
        # Handle unreachable infrastructure
        if isinstance(audit_result, Exception):
            data_to_save = {
                "name": name,
                "status": "offline",
                "error_message": str(audit_result),
                "collected_at": datetime.utcnow().isoformat() + "Z"
            }
            logger.warning(f"Node '{name}' is unreachable. Registering offline state.")
        else:
            # Serialize model output
            data_to_save = audit_result.model_dump() if hasattr(audit_result, 'model_dump') else audit_result
        
        if name == "github":
            registry.update_github_ecosystem(reg_data, identifier, data_to_save)
        elif name == "cloudflare":
            reg_data["environment_registry"]["cloud_infrastructure"] = data_to_save
        else:
            registry.update_node_audit(reg_data, name, data_to_save)
        
        logger.info(f"Successfully processed telemetry for node: {name}")

    # Report Drift & Export Artifact
    drift = dict_diff(prev_reg, reg_data)
    
    drift_file = PROJECT_ROOT / "docs" / "audit_output" / "latest_drift_report.txt"
    drift_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(drift_file, "w") as df:
        if drift:
            df.write(f"=== CONFIGURATION DRIFT DETECTED: {datetime.utcnow().isoformat()}Z ===\n")
            for d in drift: 
                logger.warning(d)
                df.write(f"{d}\n")
        else:
            msg = "No configuration drift detected."
            logger.info(msg)
            df.write(f"{msg}\n")
            
    logger.info(f"Drift artifact saved to: {drift_file}")
    
    registry.save(reg_data)
    logger.info("=== REGISTRY MERGE COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
