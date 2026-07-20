# Path: src/modules/github_api.py
import httpx
from models.github import GithubAudit
from datetime import datetime

class GitHubAuditor:
    def __init__(self, org: str, token: str):
        self.org = org
        self.headers = {"Authorization": f"Bearer {token}"}
        self.url = "https://api.github.com/graphql"

    async def audit(self) -> GithubAudit:
        query = {
            "query": """
            query($org: String!) {
              organization(login: $org) {
                repositories(first: 100) {
                  nodes {
                    name
                    diskUsage
                  }
                }
              }
            }
            """,
            "variables": {"org": self.org}
        }
        
        async with httpx.AsyncClient(headers=self.headers) as client:
            response = await client.post(self.url, json=query)
            response.raise_for_status()
            result = response.json()
            
            # Map raw response to model
            data = {
                "name": self.org,
                "collected_at": datetime.utcnow().isoformat(),
                "billing_telemetry": {"actions_minutes_used": "unavailable"}
            }
            return GithubAudit(**data)
