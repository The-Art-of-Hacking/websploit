# WebSploit Labs

WebSploit Labs is a learning environment created by Omar Santos for different Cybersecurity Ethical Hacking, Bug Hunting, Incident Response, Digital Forensics, and Threat Hunting training sessions. WebSploit Labs includes several intentionally vulnerable applications running in Docker containers on top of Kali Linux or Parrot Security OS, several additional tools, and over 9,000 cybersecurity resources.

WebSploit Labs has been used by many colleges and universities in different countries. It comes with over 500 distinct exercises!

You can obtain additional information about WebSploit Labs at: [https://websploit.org](https://websploit.org)

---

## Setting Up WebSploit Labs

### Step 1: Install Kali Linux or Parrot OS
Download and install **Kali Linux** or **Parrot OS** (whichever you prefer) in a virtual machine using the hypervisor of your choice, such as:
- VirtualBox
- VMware Workstation/Fusion
- KVM
- Proxmox (my favorite)

**Minimum VM Requirements:**
- **RAM:** 8 GB
- **CPU:** 2 vCPUs
- **Disk Space:** 50 GB

> Tip: Make sure virtualization is enabled in your system BIOS for best performance.

---

### Step 2: Install WebSploit Labs
Once your Kali or Parrot VM is ready, open a terminal and run the following commands to clone the repository and set up WebSploit Labs:

```bash
git clone https://github.com/The-Art-of-Hacking/websploit.git
cd websploit
sudo bash install.sh
```

This script will:
- Install all necessary tools
- Set up Docker
- Deploy intentionally vulnerable containers
- Add thousands of cybersecurity resources

---

## Available Containers

WebSploit Labs includes a variety of vulnerable applications organized into two networks:

### WebSploit Network (10.6.6.0/24)

#### OWASP & Classic Vulnerable Applications

| Container | IP Address | Description |
|-----------|------------|-------------|
| **webgoat** | 10.6.6.11 | OWASP WebGoat - Comprehensive web security training |
| **juice-shop** | 10.6.6.12 | OWASP Juice Shop - Modern vulnerable web app with CTF challenges |
| **dvwa** | 10.6.6.13 | Damn Vulnerable Web Application - Classic security training |

#### CTF & Challenge Containers

| Container | IP Address | Description |
|-----------|------------|-------------|
| **galactic-archives** | 10.6.6.20 | Sci-Fi themed CTF challenge |
| **gravemind** | 10.6.6.23 | Halo-themed CTF challenge |
| **y-wing** | 10.6.6.26 | Star Wars themed CTF challenge |

#### Additional Vulnerability Labs

Custom-built labs focusing on specific vulnerability categories. These labs are built from the `./additional-labs/` directory.

| Container | IP Address | Port | Vulnerability Type |
|-----------|------------|------|-------------------|
| **hydra-nexus** | 10.6.6.30 | 5010 | Multi-Vulnerability Gauntlet (SQLi, XSS, IDOR, XXE, etc.) |
| **phantom-script** | 10.6.6.31 | 5011 | Cross-Site Scripting (Reflected, Stored, DOM) |
| **trojan-relay** | 10.6.6.32 | 5012 | Server-Side Request Forgery (SSRF) |
| **sqli-breach** | 10.6.6.33 | 5001 | SQL Injection |
| **shell-inject** | 10.6.6.34 | 5002 | OS Command Injection |
| **maze-walker** | 10.6.6.35 | 5003 | Path/Directory Traversal |
| **entity-smuggler** | 10.6.6.36 | 5013 | XML External Entity (XXE) Injection |
| **token-tower** | 10.6.6.40 | 5020 | JWT Vulnerability |
| **render-reign** | 10.6.6.41 | 5021 | Server-Side Template Injection |
| **deserial-gate** | 10.6.6.42 | 5022 | Insecure Deserialization |
| **redis-rogue** | 10.6.6.43 | - | DEF CON 31 Challenge |
| **graphql-galaxy** | 10.6.6.44 | 5023 | GraphQL Introspection, IDOR |
| **proto-pollute** | 10.6.6.45 | 5004 | Prototype Pollution / DOM Clobbering |

---

## Quick Start Commands

```bash
# Start all containers
docker compose up -d

# Start with build (for additional labs)
docker compose up -d --build

# View running containers
docker compose ps

# View logs
docker compose logs -f [container_name]

# Stop all containers
docker compose down

# Rebuild specific containers
docker compose build --no-cache [container_name]
```

---

## Network Topology


```
┌─────────────────────────────────────────────────────────────┐
│           WebSploit Network (10.6.6.0/24)                   │
├─────────────────────────────────────────────────────────────┤
│  OWASP & Classic Vulnerable Applications:                   │
│  ├── webgoat     10.6.6.11                                  │
│  ├── juice-shop  10.6.6.12                                  │
│  └── dvwa        10.6.6.13                                  │
|                                                             │
│  Labs created by Omar Santos:                               │
│  ├── galactic-archives 10.6.6.20                            │
│  ├── gravemind         10.6.6.23                            │
│  ├── y-wing            10.6.6.26                            │
│  ├── hydra-nexus       10.6.6.30                            │
│  ├── phantom-script    10.6.6.31                            │
│  ├── trojan-relay      10.6.6.32                            │
│  ├── sqli-breach       10.6.6.33                            │
│  ├── shell-inject      10.6.6.34                            │
│  ├── maze-walker       10.6.6.35                            │
│  ├── entity-smuggler   10.6.6.36                            │
│  ├── token-tower       10.6.6.40                            │
│  ├── render-reign      10.6.6.41                            │
│  ├── deserial-gate     10.6.6.42                            │
│  ├── redis-rogue       10.6.6.43                            │
│  ├── graphql-galaxy    10.6.6.44                            │
│  └── proto-pollute     10.6.6.45                            │
└─────────────────────────────────────────────────────────────┘
```



---

## Troubleshooting

### Apple Silicon (M1/M2/M3/M4) and other ARM64 hosts

Several containers in this lab (`webgoat`, `dvwa`, `galactic-archives`, `gravemind`, `y-wing`, `redis-rogue`) are configured to run as `linux/amd64` and therefore run under emulation on ARM64 hosts. Most work fine, but some — notably **`y-wing`** — are Go binaries that crash under QEMU user-mode emulation with errors like:

```
runtime: lfstack.push invalid packing
fatal error: lfstack.push
```

This is a known incompatibility between Go's runtime pointer packing and QEMU's x86-on-ARM emulation. It is not a configuration bug in this repo — see [issue #82](https://github.com/The-Art-of-Hacking/websploit/issues/82).

Pick whichever option fits your setup:

#### Option 1 (recommended for Apple Silicon): Use Docker Desktop with Rosetta 2

Run Docker Desktop directly on macOS (instead of Docker inside a Kali ARM VM) so amd64 emulation goes through Apple's Rosetta 2, which handles Go binaries reliably:

1. Docker Desktop → **Settings → General** → enable **"Use Virtualization framework"**
2. Docker Desktop → **Settings → General** → enable **"Use Rosetta for x86_64/amd64 emulation on Apple Silicon"**
3. Restart Docker Desktop, then `docker compose up -d`.

You can still run Kali in a separate VM for the offensive tooling and reach the labs over the network at the documented `10.6.6.x` addresses (or via host-port mappings).

#### Option 2: Run on an x86_64 host

Use the supplied `Vagrantfile` on an Intel/AMD machine, or deploy to any x86_64 cloud VM (AWS, GCP, Azure, DigitalOcean, etc.). No emulation involved, everything works as designed.

#### Option 3: Install QEMU binfmt handlers (helps most amd64 images, not y-wing)

Inside an ARM Linux host (e.g., Kali on UTM), register multi-arch handlers before bringing the stack up:

```bash
sudo docker run --privileged --rm tonistiigi/binfmt --install amd64
sudo docker compose up -d
```

This makes most amd64 containers run, but `y-wing` will still crash because of the Go-runtime issue described above.

#### Option 4: Skip y-wing

If you cannot use options 1–3, start everything except `y-wing`:

```bash
docker compose up -d $(docker compose config --services | grep -v '^y-wing$')
```

Or comment out the `y-wing` service block in `docker-compose.yml`. The rest of the labs are independent.

---

## Disclaimer

> **WARNING**: These applications are **intentionally vulnerable**. They are **NOT malware or malicious**. They are only for educational purposes.
> - Do **NOT** expose these containers to the public internet or untrusted networks.
> - Run them only in a safe, isolated environment.
> - Use them for educational and authorized testing purposes only.
