# WebSploit Additional Labs

This directory contains an additional collection of vulnerable web applications created by Omar Santos for WebSploit Labs designed for educational purposes. These labs cover specific web vulnerabilities in isolated environments.

> **Note:** These labs are now integrated into the main `docker-compose.yml` in the root directory and run on the primary `websploit` network (10.6.6.0/24).

## Labs Overview

| Container Name | Vulnerability Type | Host URL | Internal IP |
|----------------|-------------------|----------|-------------|
| **hydra-nexus** | Multiple (SQLi, XSS, IDOR, etc.) | `http://localhost:5010` | `10.6.6.30` |
| **phantom-script** | Cross-Site Scripting (Reflected, Stored, DOM) | `http://localhost:5011` | `10.6.6.31` |
| **trojan-relay** | Server-Side Request Forgery | `http://localhost:5012` | `10.6.6.32` |
| **sqli-breach** | SQL Injection (Login Bypass) | `http://localhost:5001` | `10.6.6.33` |
| **shell-inject** | OS Command Injection | `http://localhost:5002` | `10.6.6.34` |
| **maze-walker** | Directory/Path Traversal | `http://localhost:5003` | `10.6.6.35` |
| **entity-smuggler** | XML External Entity (XXE) Injection | `http://localhost:5013` | `10.6.6.36` |

### Container Naming Theme

The containers follow a sci-fi/cybersecurity naming convention:

- **hydra-nexus** — Like the mythical multi-headed hydra, this lab has many vulnerability heads
- **phantom-script** — Scripts that haunt the DOM, invisible yet dangerous
- **trojan-relay** — Requests masquerading through the server like a Trojan horse
- **sqli-breach** — Breaching the database oracle to extract secrets
- **shell-inject** — When user input becomes system commands
- **maze-walker** — Traversing forbidden paths through the file system labyrinth
- **entity-smuggler** — External entities smuggling data through XML parsing

## Getting Started

### Prerequisites
- Docker
- Docker Compose

### Running the Labs

These labs are now part of the main WebSploit environment. From the **root directory** of the project:

1. Build and start all containers (including the additional labs):
   ```bash
   docker compose up -d --build
   ```

2. Or start only the additional labs:
   ```bash
   docker compose up -d hydra-nexus phantom-script trojan-relay sqli-breach shell-inject maze-walker entity-smuggler
   ```

3. Verify containers are running:
   ```bash
   docker compose ps
   ```

4. Access the labs using the URLs listed above.

### Stopping the Labs

To stop all containers:
```bash
docker compose down
```

To stop only the additional labs:
```bash
docker compose stop hydra-nexus phantom-script trojan-relay sqli-breach shell-inject maze-walker entity-smuggler
```

### Rebuilding After Changes

If you modify the lab source code:
```bash
docker compose build --no-cache hydra-nexus phantom-script trojan-relay sqli-breach shell-inject maze-walker entity-smuggler
docker compose up -d
```

## Lab Details

| Container | Description |
|-----------|-------------|
| **hydra-nexus** | A comprehensive multi-vulnerability gauntlet featuring SQLi, Command Injection, File Uploads, IDOR, XXE, Deserialization, JWT issues, and more. The ultimate training ground. |
| **phantom-script** | Dedicated XSS environment for practicing Reflected, Stored, and DOM-based Cross-Site Scripting attacks with varying difficulty levels. |
| **trojan-relay** | SSRF training lab with various scenarios including internal port scanning, cloud metadata access, and protocol smuggling techniques. |
| **sqli-breach** | A login portal vulnerable to SQL Injection authentication bypass. Practice union-based, error-based, and blind SQLi techniques. |
| **shell-inject** | Network tool simulator that demonstrates OS command injection vulnerabilities. Learn filter bypass and chaining techniques. |
| **maze-walker** | File viewer application with path traversal vulnerabilities. Practice LFI, directory traversal, null byte injection, and filter bypasses. |
| **entity-smuggler** | XML processing gateway vulnerable to XXE injection. Practice file disclosure, SSRF via XML, blind XXE, and entity expansion attacks. |

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  WebSploit Network (10.6.6.0/24)            │
├─────────────────────────────────────────────────────────────┤
│  Additional Labs:                                           │
│  ├── hydra-nexus     10.6.6.30:5010                        │
│  ├── phantom-script  10.6.6.31:5011                        │
│  ├── trojan-relay    10.6.6.32:5012                        │
│  ├── sqli-breach     10.6.6.33:5000 → localhost:5001       │
│  ├── shell-inject    10.6.6.34:5000 → localhost:5002       │
│  ├── maze-walker     10.6.6.35:81   → localhost:5003       │
│  └── entity-smuggler 10.6.6.36:5013                        │
└─────────────────────────────────────────────────────────────┘
```

## Disclaimer

> **WARNING**: These applications are intentionally vulnerable.
> - Do **NOT** expose these containers to the public internet.
> - Run them only in a safe, isolated environment (like the provided Docker network).
> - Use them for educational and testing purposes only.
