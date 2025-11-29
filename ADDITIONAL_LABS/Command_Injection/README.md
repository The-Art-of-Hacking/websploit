# Command Injection Lab

This lab demonstrates an OS Command Injection vulnerability in a web application.

## Scenario
The application is a "Network Diagnostics" tool that allows users to ping an IP address. The application takes the user input and passes it directly to a system shell command without proper sanitization.

## Goal
Exploit the command injection vulnerability to execute arbitrary commands on the underlying server.

## Instructions

1. **Access the Lab**: 
   - URL: `http://localhost:5002`
   
2. **Analyze functionality**:
   - Enter an IP address (e.g., `127.0.0.1`) and click "Ping".
   - Observe the output.

3. **Identify Vulnerability**:
   - Try appending shell operators to your input. Common operators include `;`, `&&`, `|`.
   - Example: `127.0.0.1; whoami`

4. **Challenge**:
   - List the files in the current directory (`ls -la`).
   - Find the current user ID (`id`).
   - Read the `/etc/passwd` file.

## Explanation
The application constructs a shell command like this:
```python
command = f"ping -c 3 {target}"
subprocess.run(command, shell=True, ...)
```
Because `shell=True` is used and `target` is not sanitized, an attacker can terminate the `ping` command and start a new one.

