#!/bin/bash
# Path: ./scripts/infrastructure_audit.sh

run_infrastructure_audit() {
    local host_ip=$1
    local user=$2
    local pass=$3
    local audit_scope=$4
    local host_name=$5
    local output_dir=$6

    echo "=== AUDITING $host_name (Scope: $audit_scope) ==="

    local docker_data="docker_status: 'not_requested'"
    local network_data="network_interfaces: 'not_requested'"
    local storage_data="storage_usage: 'not_requested'"
    local ssh_data="ssh_keys: 'not_requested'"
    
    local heuristics_data="system_heuristics:
  load_average: \"\$(uptime | awk -F'load average:' '{print \$2}' | sed 's/^[ \t]*//' || echo 'unknown')\"
  memory_active: \"\$(free | awk '/^Mem:/ {if (\$2 > 100000) print int(\$3/1024)\"MB used / \"int(\$2/1024)\"MB total\"; else print \$3\"MB used / \"\$2\"MB total\"}' || echo 'unknown')\"
  zram_status:
\$(zramctl --output NAME,DISKSIZE,DATA,COMPR --noheadings 2>/dev/null | awk '{print \"    - \" \$0}' || echo '    - not_configured')
  hardware_accelerators:
\$(lspci 2>/dev/null | grep -iE 'nvidia|coral|google|vga|3d' | awk '{print \"    - \" \$0}' || echo '    - none_detected')"

    if [[ "$audit_scope" == *"docker"* ]]; then
        docker_data="docker_status:
  driver: \"\$(docker info --format '{{.Driver}}' 2>/dev/null || echo 'not_installed')\"
  root_dir: \"\$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo 'n/a')\""
    fi

    if [[ "$audit_scope" == *"network"* ]]; then
        network_data="network_interfaces:
\$(ip -o link show | awk '{print \"  - \" \$2}' | tr -d ':')"
    fi

    if [[ "$audit_scope" == *"storage"* ]]; then
        storage_data="storage_usage:
  root_partition: \"\$(df -h / | tail -1 | awk '{print \$5}')\"
  docker_partition: \"\$(df -h \$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo /) | tail -1 | awk '{print \$5}')\""
    fi

    if [[ "$audit_scope" == *"ssh"* ]]; then
        ssh_data="ssh_keys_verified: \"\$(for f in ~/.ssh/authorized_keys /etc/dropbear/authorized_keys; do if [ -f \$f ]; then keys=\$(ssh-keygen -l -f \$f 2>/dev/null | head -n 1); [ -n \"\$keys\" ] && echo \"\$keys\" || echo \"file_empty\"; break; fi; done || echo 'none_found')\""
    fi

    sshpass -p "$pass" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$user@$host_ip" "cat <<EOF
name: '$host_name'
collected_at: '$(date -u +"%Y-%m-%dT%H:%M:%SZ")'
$heuristics_data
$docker_data
$network_data
$storage_data
$ssh_data
EOF" > "$output_dir/${host_name,,}_facts.yaml" 2>/dev/null

    if [ $? -eq 0 ]; then
        echo "Successfully audited $host_name"
    else
        echo "Failed audit for $host_name (Check credentials)"
    fi
}
