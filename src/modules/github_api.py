# Path: src/modules/github_api.py

import httpx
import logging
from models.github import GithubAudit
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class GitHubAuditor:
    def __init__(self, org: str, token: str):
        self.org = org
        self.headers = {"Authorization": f"Bearer {token}"}
        self.url = "https://api.github.com/graphql"

    async def audit(self) -> GithubAudit:
        try:
            query = """
            query($org: String!, $cursor: String) {
              organization(login: $org) {
                repositories(first: 100, after: $cursor) {
                  pageInfo {
                    hasNextPage
                    endCursor
                  }
                  nodes {
                    name
                    diskUsage
                    isArchived
                    isFork
                    isPrivate
                    stargazerCount
                    forkCount
                    primaryLanguage { name }
                    licenseInfo { name }
                    issues(states: OPEN) { totalCount }
                    pullRequests(states: OPEN) { totalCount }
                  }
                }
              }
            }
            """
            
            repositories = []
            has_next_page = True
            cursor = None

            async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
                while has_next_page:
                    variables = {"org": self.org, "cursor": cursor}
                    response = await client.post(self.url, json={"query": query, "variables": variables})
                    response.raise_for_status()
                    result = response.json()
                    
                    org_data = result.get("data", {}).get("organization", {})
                    if not org_data:
                        break
                        
                    repos_data = org_data.get("repositories", {})
                    repositories.extend(repos_data.get("nodes", []))
                    
                    page_info = repos_data.get("pageInfo", {})
                    has_next_page = page_info.get("hasNextPage", False)
                    cursor = page_info.get("endCursor")

                # Map raw response to model
                metrics = []
                archived = []
                for repo in repositories:
                    if repo.get("isArchived"):
                        archived.append({"repo": repo.get("name"), "last_pushed": "None"})
                    elif not repo.get("isFork"):
                        metrics.append({
                            "repo": repo.get("name"),
                            "description": "None",
                            "private": repo.get("isPrivate", False),
                            "default_branch": "None",
                            "language": repo.get("primaryLanguage", {}).get("name") if repo.get("primaryLanguage") else "None",
                            "license": repo.get("licenseInfo", {}).get("name") if repo.get("licenseInfo") else "None",
                            "topics": "None",
                            "stars": repo.get("stargazerCount", 0),
                            "forks": repo.get("forkCount", 0),
                            "disk_usage_kb": repo.get("diskUsage", 0),
                            "open_issues": repo.get("issues", {}).get("totalCount", 0),
                            "open_prs": repo.get("pullRequests", {}).get("totalCount", 0),
                            "last_pushed": "None"
                        })

                data = {
                    "name": self.org,
                    "collected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "billing_telemetry": {"actions_minutes_used": "unavailable", "storage_days_used": "unavailable"},
                    "repository_metrics": metrics,
                    "archived_repositories": archived
                }
                return GithubAudit(**data)
                
        except Exception as e:
            logger.error(f"GitHub API Audit failed for org {self.org}: {e}")
            raise
