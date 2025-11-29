# WebSploit Additional Labs

This directory contains an additional collection of vulnerable web applications created by Omar Santos for WebSploit Labs designed for educational purposes. These labs cover specific web vulnerabilities in isolated environments.

## Labs Overview

| Lab Name | Vulnerability | URL (Host) | Internal IP |
|----------|---------------|------------|-------------|
| **Multi-Vulnerability Gauntlet** | Multiple (SQLi, XSS, IDOR, etc.) | `http://localhost:5010` | `10.66.66.22` |
| **XSS Lab** | Cross-Site Scripting (Reflected, Stored, DOM) | `http://localhost:5011` | `10.66.66.23` |
| **SSRF Lab** | Server-Side Request Forgery | `http://localhost:5012` | `10.66.66.24` |
| **SQLi Lab** | SQL Injection (Login Bypass) | `http://localhost:5001` | `10.66.66.25` |
| **Command Injection Lab** | OS Command Injection | `http://localhost:5002` | `10.66.66.26` |
| **Path Traversal Lab** | Directory/Path Traversal | `http://localhost:5003` | `10.66.66.27` |

## Getting Started

### Prerequisites
- Docker
- Docker Compose

### Running the Labs

1. Navigate to this directory:
   ```bash
   cd ADDITIONAL_LABS
   ```

2. Build and start the containers:
   ```bash
   docker-compose up --build -d
   ```

3. Verify containers are running:
   ```bash
   docker-compose ps
   ```

4. Access the labs using the URLs listed above.

### Stopping the Labs

To stop and remove the containers:
```bash
docker-compose down
```

## Lab Details

- **Multi-Vulnerability Gauntlet**: A comprehensive app featuring SQLi, Command Injection, File Uploads, IDOR, XXE, Deserialization, JWT issues, and more.
- **XSS Lab**: Dedicated environment for practicing different types of Cross-Site Scripting attacks.
- **SSRF Lab**: Focuses on Server-Side Request Forgery with various scenarios including internal scanning and metadata access.
- **SQLi Lab**: A simple login portal vulnerable to SQL Injection authentication bypass.
- **Command Injection Lab**: A network tool simulator that allows execution of arbitrary system commands.
- **Path Traversal Lab**: A file viewer application that fails to sanitize file paths, allowing access to system files.

## Disclaimer

**WARNING**: These applications are intentionally vulnerable. 
- Do **NOT** expose these containers to the public internet.
- Run them only in a safe, isolated environment (like the provided Docker network).
- Use them for educational and testing purposes only.

