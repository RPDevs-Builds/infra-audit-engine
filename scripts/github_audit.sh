#!/bin/bash
# Path: ./scripts/github_audit.sh

run_github_audit() {
    local target_org=$1
    local token=$2
    local audit_scope=$3
    local output_dir=$4

    echo "=== AUDITING GITHUB ORG: $target_org (Scope: $audit_scope) ==="
    
    export GH_TOKEN="$token"

    local secrets_data="secrets: 'not_requested'"
    local vars_data="variables: 'not_requested'"
    local runners_data="active_runners: 'not_requested'"
    local alerts_data="vulnerability_alerts: 'not_requested'"
    local archived_data="archived_repositories: 'not_requested'"
    local forked_data="forked_repositories: 'not_requested'"
    local metrics_data="repository_metrics: 'not_requested'"
    local billing_data="billing_telemetry: 'not_requested'"

    if [[ "$audit_scope" == *"secrets"* ]]; then
        secrets_data="secrets:
$(gh secret list --org "$target_org" 2>/dev/null | awk '{print "  - name: \""$1"\"\n    updated: \""$2"\""}' || echo '  - none_accessible')"
    fi

    if [[ "$audit_scope" == *"variables"* ]]; then
        vars_data="variables:
$(gh variable list --org "$target_org" 2>/dev/null | awk '{print "  - name: \""$1"\"\n    value: \""$2"\""}' || echo '  - none_accessible')"
    fi

    if [[ "$audit_scope" == *"runners"* ]]; then
        runners_data="active_runners:
$(gh api /orgs/"$target_org"/actions/runners --jq '.runners[]? | "  - name: \"\(.name)\"\n    status: \"\(.status)\"\n    busy: \(.busy)"' 2>/dev/null || echo '  - none_found')"
    fi

    if [[ "$audit_scope" == *"billing"* ]]; then
        # Safely capture API response to prevent 410 HTTP errors from bleeding into YAML stdout
        local actions_resp=$(gh api /orgs/"$target_org"/settings/billing/actions 2>/dev/null || echo "")
        local storage_resp=$(gh api /orgs/"$target_org"/settings/billing/shared-storage 2>/dev/null || echo "")
        
        local actions_mins=$(echo "$actions_resp" | jq -r '.total_minutes_used // empty' 2>/dev/null)
        local storage_days=$(echo "$storage_resp" | jq -r '.estimated_storage_for_month // empty' 2>/dev/null)
        
        local actions_out="  actions: 'unavailable'"
        local storage_out="  storage: 'unavailable'"
        
        if [ -n "$actions_mins" ]; then actions_out="  actions_minutes_used: $actions_mins"; fi
        if [ -n "$storage_days" ]; then storage_out="  storage_days_used: $storage_days"; fi
        
        billing_data="billing_telemetry:
$actions_out
$storage_out"
    fi

    local graphql_query='
    query($org: String!, $endCursor: String) {
      organization(login: $org) {
        repositories(first: 100, after: $endCursor) {
          pageInfo { hasNextPage endCursor }
          nodes {
            name
            description
            isArchived
            isFork
            isPrivate
            pushedAt
            diskUsage
            stargazerCount
            forkCount
            primaryLanguage { name }
            licenseInfo { name }
            repositoryTopics(first: 10) {
              nodes {
                topic { name }
              }
            }
            defaultBranchRef { name }
            issues(states: OPEN) { totalCount }
            pullRequests(states: OPEN) { totalCount }
            vulnerabilityAlerts(first: 100, states: OPEN) {
              nodes {
                securityVulnerability { severity }
              }
            }
          }
        }
      }
    }'

    echo "Executing unified GraphQL telemetry fetch for $target_org..."
    local graphql_payload=$(gh api graphql --paginate -f org="$target_org" -f query="$graphql_query" 2>/dev/null)

    if [[ "$audit_scope" == *"metrics"* ]]; then
        local metrics_output=$(echo "$graphql_payload" | jq -r '
          .. | objects | .repositories?.nodes[]? 
          | select(.isArchived == false and .isFork == false)
          | "  - repo: \"\(.name)\"\n    description: \"\(if .description then (.description | gsub("\""; "'\''") | gsub("\n"; " ")) else "None" end)\"\n    private: \(.isPrivate // false)\n    default_branch: \"\(.defaultBranchRef.name // "None")\"\n    language: \"\(.primaryLanguage.name // "None")\"\n    license: \"\(.licenseInfo.name // "None")\"\n    topics: \"\(if .repositoryTopics.nodes | length > 0 then (.repositoryTopics.nodes | map(.topic.name) | join(", ")) else "None" end)\"\n    stars: \(.stargazerCount // 0)\n    forks: \(.forkCount // 0)\n    disk_usage_kb: \(.diskUsage // 0)\n    open_issues: \(.issues.totalCount // 0)\n    open_prs: \(.pullRequests.totalCount // 0)\n    last_pushed: \"\(.pushedAt // "None")\""
        ' 2>/dev/null)
        
        if [ -n "$metrics_output" ]; then
            metrics_data="repository_metrics:
$metrics_output"
        else
            metrics_data="repository_metrics:
  - none_found"
        fi
    fi

    if [[ "$audit_scope" == *"archived"* ]]; then
        local archived_output=$(echo "$graphql_payload" | jq -r '
          .. | objects | .repositories?.nodes[]? 
          | select(.isArchived == true) 
          | "  - repo: \"\(.name)\"\n    last_pushed: \"\(.pushedAt // "None")\""
        ' 2>/dev/null)
        
        if [ -n "$archived_output" ]; then
            archived_data="archived_repositories:
$archived_output"
        else
            archived_data="archived_repositories:
  - none_found"
        fi
    fi
    
    if [[ "$audit_scope" == *"forked"* ]]; then
        local forked_output=$(echo "$graphql_payload" | jq -r '
          .. | objects | .repositories?.nodes[]? 
          | select(.isFork == true) 
          | "  - repo: \"\(.name)\"\n    last_pushed: \"\(.pushedAt // "None")\""
        ' 2>/dev/null)
        
        if [ -n "$forked_output" ]; then
            forked_data="forked_repositories:
$forked_output"
        else
            forked_data="forked_repositories:
  - none_found"
        fi
    fi

    if [[ "$audit_scope" == *"alerts"* ]]; then
        echo "Querying Dependabot vulnerability alerts (excluding forks and archived)..."
        local alerts_output=$(echo "$graphql_payload" | jq -r '
          .. | objects | .repositories?.nodes[]? 
          | select(.isArchived == false and .isFork == false)
          | .name as $repo
          | (.vulnerabilityAlerts.nodes | map(.securityVulnerability.severity)) as $severities
          | ($severities | map(select(. == "CRITICAL")) | length) as $critical
          | ($severities | map(select(. == "HIGH")) | length) as $high
          | select($critical > 0 or $high > 0)
          | "  - repo: \"\($repo)\"\n    critical: \($critical)\n    high: \($high)\""
        ' 2>/dev/null)
        
        if [ -n "$alerts_output" ]; then
            alerts_data="vulnerability_alerts:
$alerts_output"
        else
            alerts_data="vulnerability_alerts:
  - none_found"
        fi
    fi

    cat <<EOF > "$output_dir/${target_org,,}_github_facts.yaml"
name: '$target_org'
collected_at: '$(date -u +"%Y-%m-%dT%H:%M:%SZ")'
$secrets_data
$vars_data
$runners_data
$billing_data
$metrics_data
$alerts_data
$archived_data
$forked_data
EOF
    
    if [ $? -eq 0 ]; then
        echo "Successfully audited GitHub org $target_org"
    else
        echo "Failed audit for GitHub org $target_org"
    fi
}
