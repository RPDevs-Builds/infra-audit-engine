#!/bin/bash
# Path: ./scripts/update_registry.sh

# Resolve script directory to handle relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REGISTRY="$PROJECT_ROOT/docs/CURRENT_ENV.yml"
TEMP_DIR="$PROJECT_ROOT/docs/audit_output"

echo "=== UPDATING CURRENT_ENV.yml REGISTRY ==="

if ! command -v yq >/dev/null 2>&1; then
    echo "Error: yq is not installed. Exiting."
    exit 1
fi

if [ ! -f "$REGISTRY" ]; then
    echo "Error: Target registry $REGISTRY not found."
    exit 1
fi

# 1. Identity & Security (Static Files)
[ -f "$TEMP_DIR/iamrpdev_gpg_keys.json" ] && yq -i '.environment_registry.security_identity.gpg_keys = load("'$TEMP_DIR'/iamrpdev_gpg_keys.json")' "$REGISTRY"

# 2. Infrastructure Runner Status (Legacy JSON Artifacts)
[ -f "$TEMP_DIR/llmadmin_runners.json" ] && yq -i '.environment_registry.nodes.llmadmin01.runners = load("'$TEMP_DIR'/llmadmin_runners.json")' "$REGISTRY"
[ -f "$TEMP_DIR/t430_runners.json" ] && yq -i '.environment_registry.nodes.t430.runners = load("'$TEMP_DIR'/t430_runners.json")' "$REGISTRY"

# 3. Project Artifacts & Repository Inventory
[ -f "$TEMP_DIR/rpdevs_vault_packages.json" ] && yq -i '.environment_registry.registry_artifacts.packages = load("'$TEMP_DIR'/rpdevs_vault_packages.json")' "$REGISTRY"
[ -f "$TEMP_DIR/iamrpdev_repos.json" ] && yq -i '.environment_registry.project_inventory.repos = load("'$TEMP_DIR'/iamrpdev_repos.json")' "$REGISTRY"

# ---------------------------------------------------------
# 4. DYNAMIC INFRASTRUCTURE (SSH) MERGE
# ---------------------------------------------------------
for fact_file in "$TEMP_DIR"/*_facts.yaml; do
    [ -e "$fact_file" ] || continue
    
    if [[ "$fact_file" == *"_github_facts.yaml" ]]; then continue; fi
    
    node_name=$(basename "$fact_file" _facts.yaml)
    
    yq -i ".environment_registry.nodes.${node_name}.latest_audit = load(\"$fact_file\")" "$REGISTRY"
done

# ---------------------------------------------------------
# 5. DYNAMIC GITHUB ECOSYSTEM (API) MERGE
# ---------------------------------------------------------
for gh_file in "$TEMP_DIR"/*_github_facts.yaml; do
    [ -e "$gh_file" ] || continue
    
    filename=$(basename "$gh_file" _github_facts.yaml)
    org_key="${filename//-/_}"
    
    yq -i ".environment_registry.github_ecosystem.${org_key} = load(\"$gh_file\")" "$REGISTRY"
done

echo "Registry merged successfully."
