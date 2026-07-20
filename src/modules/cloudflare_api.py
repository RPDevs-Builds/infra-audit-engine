# Path: /mnt/sharedroot/projects/llm-userprofile/AUDIT/src/modules/cloudflare_api.py

import httpx
import logging
from models.cloudflare import CloudflareAudit
from datetime import datetime

logger = logging.getLogger(__name__)

class CloudflareAuditor:
    def __init__(self, account_id: str, token: str, scope: list, output_dir: str):
        self.account_id = account_id
        self.headers = {"Authorization": f"Bearer {token}"}
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.scope = scope

    async def audit(self) -> CloudflareAudit:
        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            try:
                resp_zones = await client.get(f"{self.base_url}/zones")
                zones = resp_zones.json().get("result", [])
                dns_records = {}
                for zone in zones:
                    z_id = zone['id']
                    z_name = zone['name']
                    resp_dns = await client.get(f"{self.base_url}/zones/{z_id}/dns_records?per_page=100")
                    dns_records[z_name] = resp_dns.json().get("result", [])
                
                resp_tunnels = await client.get(f"{self.base_url}/accounts/{self.account_id}/cfd_tunnel")
                raw_tunnels = resp_tunnels.json().get("result", [])
                tunnels = []
                for t in raw_tunnels:
                    conf = await client.get(f"{self.base_url}/accounts/{self.account_id}/cfd_tunnel/{t['id']}/configurations")
                    ingress = conf.json().get("result", {}).get("config", {}).get("ingress", [])
                    clean_ingress = [{"hostname": rule.get("hostname", "unknown"), "service": rule.get("service", "unknown")} for rule in ingress if "hostname" in rule]
                    tunnels.append({"name": t.get("name", "unknown"), "status": t.get("status", "unknown"), "connections": len(t.get("connections", [])), "ingress_rules": clean_ingress})

                resp_access = await client.get(f"{self.base_url}/accounts/{self.account_id}/access/apps")
                access = resp_access.json().get("result", [])
                resp_workers = await client.get(f"{self.base_url}/accounts/{self.account_id}/workers/scripts")
                raw_workers = resp_workers.json().get("result", [])
                workers = [{"id": w.get("id"), "created_on": w.get("created_on")} for w in raw_workers]

                data = {
                    "collected_at": datetime.utcnow().isoformat(),
                    "zones": [{"name": z["name"], "status": z["status"], "dns_record_count": len(dns_records.get(z["name"], []))} for z in zones],
                    "dns_records": dns_records,
                    "tunnels": tunnels,
                    "access_apps": access,
                    "workers": workers
                }
                return CloudflareAudit(**data)
            except Exception as e:
                logger.error(f"Cloudflare API Audit failed: {e}")
                raise
