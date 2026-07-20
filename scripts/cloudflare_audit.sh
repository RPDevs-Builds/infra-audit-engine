#!/bin/bash
# Path: ./scripts/cloudflare_audit.sh

run_cloudflare_audit() {
    local account_id=$1
    local token=$2
    local audit_scope=$3
    local output_dir=$4

    echo "=== AUDITING CLOUDFLARE (Scope: $audit_scope) ==="
    
    local api_base="https://api.cloudflare.com/client/v4"
    local curl_opts=(-s -H "Authorization: Bearer $token" -H "Content-Type: application/json")

    # Verify Token Permissions securely via Zones rather than Root User scope
    local zones_resp=$(curl "${curl_opts[@]}" "$api_base/zones?per_page=1")
    local auth_success=$(echo "$zones_resp" | jq -r '.success' 2>/dev/null)

    if [ "$auth_success" != "true" ]; then
        local err_msg=$(echo "$zones_resp" | jq -r '.errors[0].message // "Verify token bindings and Account ID."' 2>/dev/null)
        echo "Error: Cloudflare API authentication failed. Reason: $err_msg"
        return 1
    fi

    local cf_data="name: 'Cloudflare'\ncollected_at: '$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"

    # Pre-fetch Zones globally for loops
    local all_zones=$(curl "${curl_opts[@]}" "$api_base/zones")

    if [[ "$audit_scope" == *"discovery"* || "$audit_scope" == *"zones"* ]]; then
        echo "Discovering Zones..."
        local zones_output=""
        for row in $(echo "$all_zones" | jq -r '.result[] | @base64' 2>/dev/null); do
            _jq() { echo ${row} | base64 --decode | jq -r ${1} 2>/dev/null; }
            local zid=$(_jq '.id')
            local zname=$(_jq '.name')
            local zstatus=$(_jq '.status')
            
            # Grabs total DNS record count metadata safely without payload overhead
            local dns_count=$(curl "${curl_opts[@]}" "$api_base/zones/$zid/dns_records?per_page=1" | jq -r '.result_info.total_count // 0' 2>/dev/null)
            
            zones_output+=$'\n'"  - name: \"$zname\""
            zones_output+=$'\n'"    status: \"$zstatus\""
            zones_output+=$'\n'"    dns_record_count: $dns_count"
        done
        
        if [ -n "$zones_output" ]; then
            cf_data+=$'\n'"zones:$zones_output"
        else
            cf_data+=$'\n'"zones:\n  - none_found"
        fi
    fi

    if [[ "$audit_scope" == *"dns"* ]]; then
        echo "Mapping Detailed DNS Records..."
        local dns_data="dns_records:"
        local zone_ids=$(echo "$all_zones" | jq -r '.result[]? | "\(.id):\(.name)"' 2>/dev/null)
        
        for z_info in $zone_ids; do
            local zid=${z_info%%:*}
            local zname=${z_info#*:}
            
            dns_data+=$'\n'"  $zname:"
            
            # Fetch up to 100 DNS records per zone
            local dns_resp=$(curl "${curl_opts[@]}" "$api_base/zones/$zid/dns_records?per_page=100")
            
            # Utilize `tojson` for bulletproof YAML serialization of complex TXT/DKIM records
            local records=$(echo "$dns_resp" | jq -r '.result[]? | "    - type: \(.type | tojson)\n      name: \(.name | tojson)\n      content: \(.content | tojson)\n      proxied: \(.proxied)"' 2>/dev/null)
            
            if [ -n "$records" ]; then
                dns_data+=$'\n'"$records"
            else
                dns_data+=$'\n'"    - none_found"
            fi
        done
        cf_data+=$'\n'"$dns_data"
    fi

    if [[ "$audit_scope" == *"discovery"* || "$audit_scope" == *"tunnels"* ]]; then
        echo "Discovering Tunnels and Ingress Routes..."
        local tunnels_data="tunnels:"
        local tunnel_resp=$(curl "${curl_opts[@]}" "$api_base/accounts/$account_id/cfd_tunnel")
        
        # Base64 decode to handle spaces in tunnel names safely
        local tunnel_ids=$(echo "$tunnel_resp" | jq -r '.result[]? | @base64' 2>/dev/null)
        
        if [ -n "$tunnel_ids" ]; then
            for row in $tunnel_ids; do
                _t_jq() { echo ${row} | base64 --decode | jq -r ${1} 2>/dev/null; }
                local tid=$(_t_jq '.id')
                local tname=$(_t_jq '.name')
                local tstatus=$(_t_jq '.status')
                
                # Fallback to empty array before evaluating length to prevent blank values
                local tconn=$(_t_jq '.connections // [] | length')

                tunnels_data+=$'\n'"  - name: \"$tname\""
                tunnels_data+=$'\n'"    status: \"$tstatus\""
                tunnels_data+=$'\n'"    connections: $tconn"
                
                # Fetch Ingress Rules
                local conf_resp=$(curl "${curl_opts[@]}" "$api_base/accounts/$account_id/cfd_tunnel/$tid/configurations")
                local routes=$(echo "$conf_resp" | jq -r '.result.config.ingress[]? | select(.hostname != null) | "      - hostname: \(.hostname | tojson)\n        service: \(.service | tojson)"' 2>/dev/null)
                
                if [ -n "$routes" ]; then
                    tunnels_data+=$'\n'"    ingress_rules:"
                    tunnels_data+=$'\n'"$routes"
                else
                    tunnels_data+=$'\n'"    ingress_rules: []"
                fi
            done
        else
            tunnels_data="tunnels:\n  - none_found"
        fi
        cf_data+=$'\n'"$tunnels_data"
    fi

    if [[ "$audit_scope" == *"discovery"* || "$audit_scope" == *"access"* ]]; then
        echo "Discovering Access Applications..."
        local access_data="access_apps:"
        local access_resp=$(curl "${curl_opts[@]}" "$api_base/accounts/$account_id/access/apps")
        
        # Secure string serialization applied to domains and access names
        local apps=$(echo "$access_resp" | jq -r '.result[]? | "  - name: \(.name | tojson)\n    domain: \(.domain | tojson)\n    aud: \(.aud | tojson)"' 2>/dev/null)
        
        if [ -n "$apps" ]; then
            access_data+=$'\n'"$apps"
        else
            access_data+="  - none_found"
        fi
        cf_data+=$'\n'"$access_data"
    fi

    if [[ "$audit_scope" == *"discovery"* || "$audit_scope" == *"workers"* ]]; then
        echo "Discovering Workers & Scripts..."
        local workers_data="workers:"
        local workers_resp=$(curl "${curl_opts[@]}" "$api_base/accounts/$account_id/workers/scripts")
        local workers=$(echo "$workers_resp" | jq -r '.result[]? | "  - name: \(.id | tojson)"' 2>/dev/null)
        
        if [ -n "$workers" ]; then
            workers_data+=$'\n'"$workers"
        else
            workers_data+="  - none_found"
        fi
        cf_data+=$'\n'"$workers_data"
    fi

    if [[ "$audit_scope" == *"discovery"* || "$audit_scope" == *"pages"* ]]; then
        echo "Discovering Pages Projects..."
        local pages_data="pages_projects:"
        local pages_resp=$(curl "${curl_opts[@]}" "$api_base/accounts/$account_id/pages/projects")
        
        # Array length null-protection applied
        local pages=$(echo "$pages_resp" | jq -r '.result[]? | "  - name: \(.name | tojson)\n    domains: \(.domains // [] | length)"' 2>/dev/null)
        
        if [ -n "$pages" ]; then
            pages_data+=$'\n'"$pages"
        else
            pages_data+="  - none_found"
        fi
        cf_data+=$'\n'"$pages_data"
    fi

    echo -e "$cf_data" > "$output_dir/cloudflare_api_facts.yaml"
    echo "Successfully audited Cloudflare API."
}
