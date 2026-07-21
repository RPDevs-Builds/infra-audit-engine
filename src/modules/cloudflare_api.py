# Path: /mnt/sharedroot/projects/llm-userprofile/AUDIT/src/modules/cloudflare_api.py

import asyncio
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

    async def _fetch_zone_dns(self, client: httpx.AsyncClient, z_id: str, z_name: str):
        resp = await client.get(f"{self.base_url}/zones/{z_id}/dns_records?per_page=100")
        return z_name, resp.json().get("result", [])

    async def _fetch_tunnel_config(self, client: httpx.AsyncClient, t: dict):
        conf = await client.get(f"{self.base_url}/accounts/{self.account_id}/cfd_tunnel/{t['id']}/configurations")
        ingress = conf.json().get("result", {}).get("config", {}).get("ingress", [])
        clean_ingress = [{"hostname": rule.get("hostname", "unknown"), "service": rule.get("service", "unknown")} for rule in ingress if "hostname" in rule]
        return {
            "name": t.get("name", "unknown"), 
            "status": t.get("status", "unknown"), 
            "connections": len(t.get("connections", [])), 
            "ingress_rules": clean_ingress
        }

    async def audit(self) -> CloudflareAudit:
        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            try:
                # Fetch Zones
                resp_zones = await client.get(f"{self.base_url}/zones")
                zones = resp_zones.json().get("result", [])
                
                # Concurrently fetch DNS records for all zones
                dns_tasks = [self._fetch_zone_dns(client, zone['id'], zone['name']) for zone in zones]
                dns_results = await asyncio.gather(*dns_tasks)
                dns_records = {name: records for name, records in dns_results}
                
                # Fetch Tunnels
                resp_tunnels = await client.get(f"{self.base_url}/accounts/{self.account_id}/cfd_tunnel")
                raw_tunnels = resp_tunnels.json().get("result", [])
                
                # Concurrently fetch config for all tunnels
                tunnel_tasks = [self._fetch_tunnel_config(client, t) for t in raw_tunnels]
                tunnels = await asyncio.gather(*tunnel_tasks)

                # Fetch Access Apps and Workers concurrently
                resp_access_task = client.get(f"{self.base_url}/accounts/{self.account_id}/access/apps")
                resp_workers_task = client.get(f"{self.base_url}/accounts/{self.account_id}/workers/scripts")
                resp_access, resp_workers = await asyncio.gather(resp_access_task, resp_workers_task)

                access = resp_access.json().get("result", [])
                raw_workers = resp_workers.json().get("result", [])
                workers = [{"id": w.get("id"), "created_on": w.get("created_on")} for w in raw_workers]

                data = {
                    "collected_at": datetime.utcnow().isoformat() + "Z",
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
