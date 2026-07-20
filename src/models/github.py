# Path: /mnt/sharedroot/projects/llm-userprofile/src/models/github.py

from typing import List, Optional, Union
from pydantic import BaseModel, Field

class Secret(BaseModel):
    name: str
    updated: str

class Variable(BaseModel):
    name: str
    value: str

class Runner(BaseModel):
    name: str
    status: str
    busy: bool

class BillingTelemetry(BaseModel):
    actions_minutes_used: Union[int, str] = 'unavailable'
    storage_days_used: Union[float, str] = 'unavailable'

class RepositoryMetric(BaseModel):
    repo: str
    description: str
    private: bool
    default_branch: str
    language: str
    license: str
    topics: str
    stars: int
    forks: int
    disk_usage_kb: int
    open_issues: int
    open_prs: int
    last_pushed: str

class VulnerabilityAlert(BaseModel):
    repo: str
    critical: int
    high: int

class ArchivedRepository(BaseModel):
    repo: str
    last_pushed: str

class GithubAudit(BaseModel):
    name: str
    collected_at: str
    secrets: List[Union[Secret, str]] = Field(default_factory=list)
    variables: List[Union[Variable, str]] = Field(default_factory=list)
    active_runners: List[Union[Runner, str]] = Field(default_factory=list)
    billing_telemetry: BillingTelemetry
    repository_metrics: List[Union[RepositoryMetric, str]] = Field(default_factory=list)
    vulnerability_alerts: List[Union[VulnerabilityAlert, str]] = Field(default_factory=list)
    archived_repositories: List[Union[ArchivedRepository, str]] = Field(default_factory=list)
    forked_repositories: List[Union[ArchivedRepository, str]] = Field(default_factory=list)
