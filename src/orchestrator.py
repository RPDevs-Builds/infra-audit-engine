# Path: src/orchestrator.py

import asyncio
import logging
from datetime import datetime, timezone
from config import load_environment, get_hosts_from_env, PROJECT_ROOT
from logger import setup_system_logger

# Initialize logging BEFORE modules run to enforce third-party silencing
logger = setup_system_logger(PROJECT_ROOT)

from modules.github_api import GitHubAuditor
from modules.cloudflare_api import CloudflareAuditor
from modules.ssh_audit import InfrastructureAuditor
from registry import RegistryManager

from diff_audit import dict_diff

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
                "collected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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
            df.write(f"=== CONFIGURATION DRIFT DETECTED: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')} ===\n")
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
