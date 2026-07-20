# Infrastructure Audit Engine

An asynchronous, cross-domain state auditor and configuration drift detector. This engine aggregates runtime metrics, hardware accelerator status, and network topologies across local compute nodes, OpenWrt edge routers, and external SaaS providers (Cloudflare, GitHub). State is compiled into a normalized YAML registry to detect unauthorized or accidental configuration drift.

## Core Features

*   **Asynchronous SSH Collection:** Parallelized execution across local network nodes extracting system heuristics, ZRAM mappings, Docker configurations, and hardware accelerator states (GPU/TPU).
*   **Native OpenWrt Integration:** Direct `uci` configuration parsing for granular edge router tracking and drift detection across interfaces, firewall rules, and DHCP states.
*   **Cloudflare & GitHub Telemetry:** Pulls active tunnel metrics, DNS records, Access policies, Worker deployments, and GitHub Actions runner states.
*   **Hardware-Backed Trust:** Integrates with `age` and FIDO2 tokens to decrypt `.env.age` secrets into a volatile RAM disk (`/dev/shm`) at runtime, guaranteeing zero-footprint credentials.
*   **Noise-Filtered Drift Detection:** Compares active state against historical baselines while automatically filtering transient data (load average, memory fluctuations) to surface only actionable configuration changes.
*   **Portable Binary:** Wraps execution and dependencies into a standalone binary via PyInstaller and Make.

## Prerequisites

*   Python 3.12+
*   `make`
*   `age` (for environment decryption)
*   FIDO2 Hardware Key (configured via `chezmoi` or local `age-identity.txt`)
*   Target nodes require SSH access (Ed25519 or RSA dropbear/OpenSSH keys)

## Installation & Build

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/RPDevs-Builds/infra-audit-engine.git](https://github.com/RPDevs-Builds/infra-audit-engine.git)
   cd infra-audit-engine
