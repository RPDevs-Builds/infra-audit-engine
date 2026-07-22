# Path: src/modules/ssh_audit.py

import asyncssh
import logging
from datetime import datetime, timezone
from models.infrastructure import (
    InfrastructureAudit, OpenWrtAudit, SystemHeuristics,
    DockerStatus, StorageUsage, ZramStatus
)

logger = logging.getLogger(__name__)

class InfrastructureAuditor:
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password

    def _parse_uci_show(self, uci_stdout: str) -> dict:
        uci_data = {}
        sensitive_keys = {'key', 'password', 'passphrase', 'secret', 'token'}

        for line in uci_stdout.splitlines():
            line = line.strip()
            if not line or '=' not in line: continue
            
            key_part, val_part = line.split('=', 1)
            val_part = val_part.strip("'\"")
            
            parts = key_part.split('.')
            if len(parts) < 2: continue
                
            config, section = parts[0], parts[1]
            
            if config not in uci_data: uci_data[config] = {}
            if section not in uci_data[config]: uci_data[config][section] = {}
                
            if len(parts) == 2:
                uci_data[config][section]['_type'] = val_part
            else:
                option = ".".join(parts[2:])
                if option in sensitive_keys: val_part = "[REDACTED]"

                existing = uci_data[config][section].get(option)
                if existing is not None:
                    if isinstance(existing, list): existing.append(val_part)
                    else: uci_data[config][section][option] = [existing, val_part]
                else:
                    uci_data[config][section][option] = val_part
                    
        return uci_data

    async def get_system_stats(self, node_name: str):
        try:
            async with asyncssh.connect(self.host, username=self.user, password=self.password, known_hosts=None) as conn:
                # 1. System Heuristics
                load = await conn.run("uptime | awk -F'load average:' '{print $2}'")
                mem = await conn.run("free | awk '/^Mem:/ {print $3\"MB used / \"$2\"MB total\"}'")
                
                zram_list = []
                zram_res = await conn.run("if command -v zramctl >/dev/null; then zramctl --output NAME,DISKSIZE,DATA,COMPR -n 2>/dev/null; fi")
                if zram_res.stdout:
                    for line in zram_res.stdout.splitlines():
                        parts = line.split()
                        if len(parts) >= 4:
                            zram_list.append(ZramStatus(device=parts[0], disksize=parts[1], data=parts[2], compr=parts[3]))

                hw_res = await conn.run("command -v lspci >/dev/null && lspci | grep -iE 'VGA|3D|Coral|TPU' || echo ''")
                hw_list = [l.strip() for l in hw_res.stdout.splitlines() if l.strip()] if hw_res.stdout else []

                # 2. SSH Keys
                key_cmd = (
                    "if command -v dropbearkey >/dev/null; then "
                    "if [ -f /etc/dropbear/dropbear_ed25519_host_key ]; then dropbearkey -y -f /etc/dropbear/dropbear_ed25519_host_key | grep 'Fingerprint' | awk '{print $2}'; "
                    "elif [ -f /etc/dropbear/dropbear_rsa_host_key ]; then dropbearkey -y -f /etc/dropbear/dropbear_rsa_host_key | grep 'Fingerprint' | awk '{print $2}'; fi; "
                    "else "
                    "if [ -f /etc/ssh/ssh_host_ed25519_key.pub ]; then ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub | awk '{print $2}'; "
                    "else ssh-keygen -lf /etc/ssh/ssh_host_rsa_key.pub | awk '{print $2}'; fi; "
                    "fi"
                )
                key_res = await conn.run(key_cmd)

                # 3. Docker & Storage Metrics
                driver_res = await conn.run("docker info -f '{{.Driver}}' 2>/dev/null || echo 'unknown'")
                docker_dir_res = await conn.run("docker info -f '{{.DockerRootDir}}' 2>/dev/null || echo 'unknown'")
                docker_dir = docker_dir_res.stdout.strip() if docker_dir_res.stdout else "unknown"
                
                net_res = await conn.run("ls -1 /sys/class/net/")
                interfaces = [i.strip() for i in net_res.stdout.splitlines() if i.strip()] if net_res.stdout else []

                root_st = await conn.run("df -h / | tail -n 1 | awk '{print $5}'")
                dock_st = await conn.run(f"df -h {docker_dir} 2>/dev/null | tail -n 1 | awk '{{print $5}}'")

                # 4. Construct the Core Model Payload
                common_args = {
                    "name": node_name,
                    "collected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "system_heuristics": SystemHeuristics(
                        load_average=load.stdout.strip() if load.stdout else "unknown",
                        memory_active=mem.stdout.strip() if mem.stdout else "unknown",
                        zram_status=zram_list,
                        hardware_accelerators=hw_list
                    ),
                    "docker_status": DockerStatus(
                        driver=driver_res.stdout.strip() if driver_res.stdout else "unknown",
                        root_dir=docker_dir
                    ),
                    "network_interfaces": interfaces,
                    "storage_usage": StorageUsage(
                        root_partition=root_st.stdout.strip() if root_st.stdout else "unknown",
                        docker_partition=dock_st.stdout.strip() if dock_st.stdout else None
                    ),
                    "ssh_keys_verified": key_res.stdout.strip() if key_res.stdout else "failed"
                }

                # 5. OS Routing
                uci_check = await conn.run("command -v uci")
                if uci_check.exit_status == 0:
                    uci_output = await conn.run("uci show")
                    uci_config = self._parse_uci_show(uci_output.stdout) if uci_output.exit_status == 0 else {}
                    return OpenWrtAudit(**common_args, openwrt_config=uci_config)
                
                return InfrastructureAudit(**common_args)
                
        except Exception as e:
            logger.error(f"SSH Audit failed on {self.host}: {e}")
            raise
