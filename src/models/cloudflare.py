# Path: /mnt/sharedroot/projects/llm-userprofile/AUDIT/src/models/cloudflare.py

from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field

class Zone(BaseModel):
    name: str
    status: str
    dns_record_count: int

class DnsRecord(BaseModel):
    type: str
    name: str
    content: str
    proxied: bool

class Tunnel(BaseModel):
    name: str
    status: str
    connections: int
    ingress_rules: List[Dict[str, str]] = Field(default_factory=list)

class AccessApp(BaseModel):
    name: str
    domain: str
    aud: str

class Worker(BaseModel):
    id: str
    created_on: Optional[str] = None
    modified_on: Optional[str] = None

class CloudflareAudit(BaseModel):
    name: str = 'Cloudflare'
    collected_at: str
    zones: List[Zone] = Field(default_factory=list)
    dns_records: Dict[str, List[Union[DnsRecord, dict]]] = Field(default_factory=dict)
    tunnels: List[Union[Tunnel, dict]] = Field(default_factory=list)
    access_apps: List[Union[AccessApp, dict]] = Field(default_factory=list)
    workers: List[Worker] = Field(default_factory=list)
