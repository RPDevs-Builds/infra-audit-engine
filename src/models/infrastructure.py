# Path: /mnt/sharedroot/projects/llm-userprofile/src/models/infrastructure.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ZramStatus(BaseModel):
    device: str
    disksize: str
    data: str
    compr: str

class SystemHeuristics(BaseModel):
    load_average: str
    memory_active: str
    zram_status: Optional[List[ZramStatus]] = Field(default_factory=list)
    hardware_accelerators: Optional[List[str]] = Field(default_factory=list)

class DockerStatus(BaseModel):
    driver: str
    root_dir: str

class StorageUsage(BaseModel):
    root_partition: str
    docker_partition: Optional[str] = None

class InfrastructureAudit(BaseModel):
    name: str
    collected_at: str
    node_type: str = "linux"
    system_heuristics: SystemHeuristics
    docker_status: DockerStatus
    network_interfaces: List[str]
    storage_usage: StorageUsage
    ssh_keys_verified: str

class OpenWrtAudit(InfrastructureAudit):
    node_type: str = "openwrt"
    openwrt_config: Dict[str, Any] = Field(default_factory=dict)
