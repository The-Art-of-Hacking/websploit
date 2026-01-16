# WebSploit Additional Labs

This directory contains an additional collection of vulnerable web applications created by Omar Santos for WebSploit Labs designed for educational purposes. These labs cover specific web vulnerabilities in isolated environments.

> **Note:** These labs are now integrated into the main `docker-compose.yml` in the root directory and run on the primary `websploit` network (10.6.6.0/24).

## Directory to Container Mapping

| Directory Name | Container Name | Vulnerability / Lab Type |
| :--- | :--- | :--- |
| `Command_Injection` | `shell-inject` | Command Injection |
| `deserial-gate` | `deserial-gate` | Insecure Deserialization |
| `GraphQL` | `graphql-galaxy` | GraphQL API Hacking |
| `Multi-Vulnerability-Gauntlet` | `hydra-nexus` | Multiple Vulnerabilities |
| `Path_Traversal` | `maze-walker` | Path Traversal |
| `Prototype_Pollution` | `proto-pollute` | Prototype Pollution / DOM Clobbering |
| `render-reign` | `render-reign` | Server-Side Template Injection (SSTI) |
| `SQLi` | `sqli-breach` | SQL Injection |
| `SSRF` | `trojan-relay` | Server-Side Request Forgery |
| `token-tower` | `token-tower` | JWT / Identity Attacks |
| `XSS` | `phantom-script` | Cross-Site Scripting (XSS) |
| `XXE` | `entity-smuggler` | XML External Entity (XXE) |


# Network Topology
The following is the network topology of WebSploit Labs.

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