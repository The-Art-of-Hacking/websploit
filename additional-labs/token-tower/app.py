#!/usr/bin/env python3
"""
WebSploit Labs - Token Tower (JWT Vulnerability Lab)
Created for educational purposes by Omar Santos
This application demonstrates various JWT security vulnerabilities

Vulnerabilities included:
1. Weak signing secret (crackable)
2. None algorithm attack
3. Algorithm confusion (RS256 to HS256)
4. JWK header injection
5. Claim manipulation
6. Missing expiration validation
"""

from flask import Flask, request, render_template_string, jsonify, make_response, redirect
import jwt
import json
import base64
import datetime
import hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

# ============================================================================
# CONFIGURATION - Intentionally Weak for Educational Purposes
# ============================================================================

# Vulnerability 1: Weak secret that can be cracked
WEAK_SECRET = "secret123"

# Generate RSA keys for RS256 demonstrations
PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
PUBLIC_KEY = PRIVATE_KEY.public_key()

# Serialize keys
PRIVATE_KEY_PEM = PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

PUBLIC_KEY_PEM = PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

# Flags for different challenges
FLAGS = {
    "none_algorithm": "WEBSPLOIT{JWT_N0N3_4LG0R1THM_BYP4SS}",
    "weak_secret": "WEBSPLOIT{W34K_S3CR3T_CR4CK3D}",
    "algorithm_confusion": "WEBSPLOIT{4LG0_C0NFUS10N_M4ST3R}",
    "privilege_escalation": "WEBSPLOIT{PR1V1L3G3_3SC4L4T10N}",
    "jwk_injection": "WEBSPLOIT{JWK_1NJ3CT10N_PWN3D}",
    "master": "WEBSPLOIT{JWT_M4ST3R_H4CK3R}"
}

# User database (simulated)
USERS = {
    "admin": {"password": "supersecretadminpassword", "role": "admin", "id": 1},
    "guest": {"password": "guest", "role": "guest", "id": 2},
    "user": {"password": "password123", "role": "user", "id": 3}
}

# ============================================================================
# HTML TEMPLATES
# ============================================================================

BASE_STYLE = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        min-height: 100vh;
        color: #e4e4e4;
    }
    .container {
        max-width: 1000px;
        margin: 0 auto;
        padding: 20px;
    }
    .header {
        text-align: center;
        padding: 40px 0;
        border-bottom: 2px solid #e94560;
        margin-bottom: 30px;
    }
    .header h1 {
        color: #e94560;
        font-size: 2.5em;
        text-shadow: 0 0 20px rgba(233, 69, 96, 0.5);
        margin-bottom: 10px;
    }
    .header .subtitle {
        color: #aaa;
        font-size: 1.1em;
    }
    .card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(233, 69, 96, 0.3);
        border-radius: 10px;
        padding: 25px;
        margin: 20px 0;
        backdrop-filter: blur(10px);
    }
    .card h2 {
        color: #e94560;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .card h3 {
        color: #00d9ff;
        margin: 15px 0 10px 0;
    }
    .login-form {
        max-width: 400px;
        margin: 0 auto;
    }
    input, select {
        width: 100%;
        padding: 12px 15px;
        margin: 8px 0;
        border: 1px solid #444;
        border-radius: 6px;
        background: rgba(0,0,0,0.3);
        color: #fff;
        font-size: 1em;
    }
    input:focus {
        outline: none;
        border-color: #e94560;
        box-shadow: 0 0 10px rgba(233, 69, 96, 0.3);
    }
    button, .btn {
        background: linear-gradient(135deg, #e94560, #c23a51);
        color: white;
        padding: 12px 25px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 1em;
        width: 100%;
        margin-top: 15px;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
        text-align: center;
    }
    button:hover, .btn:hover {
        background: linear-gradient(135deg, #ff6b6b, #e94560);
        box-shadow: 0 5px 20px rgba(233, 69, 96, 0.4);
        transform: translateY(-2px);
    }
    .btn-secondary {
        background: linear-gradient(135deg, #333, #555);
    }
    .warning {
        background: rgba(255, 193, 7, 0.1);
        border: 1px solid #ffc107;
        border-left: 4px solid #ffc107;
        color: #ffc107;
        padding: 15px;
        border-radius: 6px;
        margin: 15px 0;
    }
    .success {
        background: rgba(40, 167, 69, 0.1);
        border: 1px solid #28a745;
        border-left: 4px solid #28a745;
        color: #28a745;
        padding: 15px;
        border-radius: 6px;
        margin: 15px 0;
    }
    .error {
        background: rgba(220, 53, 69, 0.1);
        border: 1px solid #dc3545;
        border-left: 4px solid #dc3545;
        color: #dc3545;
        padding: 15px;
        border-radius: 6px;
        margin: 15px 0;
    }
    .flag {
        background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(233, 69, 96, 0.1));
        border: 2px solid #00d9ff;
        color: #00d9ff;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        text-align: center;
        font-family: 'Courier New', monospace;
        font-size: 1.2em;
        animation: glow 2s ease-in-out infinite alternate;
    }
    @keyframes glow {
        from { box-shadow: 0 0 10px rgba(0, 217, 255, 0.3); }
        to { box-shadow: 0 0 30px rgba(0, 217, 255, 0.6); }
    }
    .code-block {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 15px;
        margin: 10px 0;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        overflow-x: auto;
        color: #c9d1d9;
    }
    .jwt-parts {
        word-break: break-all;
    }
    .jwt-header { color: #ff7b72; }
    .jwt-payload { color: #d2a8ff; }
    .jwt-signature { color: #79c0ff; }
    .nav {
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
        margin: 20px 0;
    }
    .nav a {
        color: #e4e4e4;
        text-decoration: none;
        padding: 8px 16px;
        border: 1px solid #444;
        border-radius: 6px;
        transition: all 0.3s ease;
    }
    .nav a:hover {
        border-color: #e94560;
        color: #e94560;
    }
    .vuln-list {
        list-style: none;
        padding: 0;
    }
    .vuln-list li {
        padding: 10px 15px;
        margin: 5px 0;
        background: rgba(0,0,0,0.2);
        border-radius: 6px;
        border-left: 3px solid #e94560;
    }
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }
    .stat-card {
        background: rgba(0,0,0,0.3);
        padding: 20px;
        border-radius: 8px;
        text-align: center;
    }
    .stat-card .value {
        font-size: 2em;
        color: #00d9ff;
        font-weight: bold;
    }
    .stat-card .label {
        color: #888;
        margin-top: 5px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    th, td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #333;
    }
    th {
        background: rgba(233, 69, 96, 0.2);
        color: #e94560;
    }
    tr:hover {
        background: rgba(255,255,255,0.02);
    }
</style>
"""

HOME_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Token Tower - JWT Vulnerability Lab</title>
    """ + BASE_STYLE + """
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗼 Token Tower</h1>
            <p class="subtitle">JWT Vulnerability Training Lab | WebSploit Labs</p>
        </div>
        
        <div class="nav">
            <a href="/">🏠 Home</a>
            <a href="/login">🔐 Login</a>
            <a href="/dashboard">📊 Dashboard</a>
            <a href="/api/docs">📚 API Docs</a>
            <a href="/public-key">🔑 Public Key</a>
            <a href="/hints">💡 Hints</a>
        </div>
        
        <div class="card">
            <h2>🎯 Challenge Overview</h2>
            <p>Welcome to Token Tower, a JWT security training environment. Your mission is to exploit various JWT vulnerabilities to gain admin access and capture all flags.</p>
            
            <h3>Vulnerabilities to Discover:</h3>
            <ul class="vuln-list">
                <li>🔓 <strong>Weak Signing Secret</strong> - Can you crack the JWT secret?</li>
                <li>⚡ <strong>None Algorithm Attack</strong> - Bypass signature verification entirely</li>
                <li>🔄 <strong>Algorithm Confusion</strong> - RS256 to HS256 confusion attack</li>
                <li>💉 <strong>JWK Header Injection</strong> - Inject your own signing key</li>
                <li>📝 <strong>Claim Manipulation</strong> - Escalate privileges through token tampering</li>
            </ul>
        </div>
        
        <div class="card">
            <h2>🚀 Getting Started</h2>
            <ol style="margin-left: 20px; line-height: 2;">
                <li>Login with credentials: <code>guest / guest</code></li>
                <li>Examine your JWT token in the cookies</li>
                <li>Analyze the token structure at jwt.io</li>
                <li>Exploit vulnerabilities to escalate to admin</li>
                <li>Capture all flags!</li>
            </ol>
        </div>
        
        <div class="warning">
            ⚠️ <strong>Educational Environment:</strong> This application contains intentional security vulnerabilities for learning purposes. Do not use these techniques on production systems without authorization.
        </div>
    </div>
</body>
</html>
"""

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Token Tower</title>
    """ + BASE_STYLE + """
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Token Tower Login</h1>
            <p class="subtitle">Authenticate to receive your JWT</p>
        </div>
        
        <div class="nav">
            <a href="/">🏠 Home</a>
            <a href="/login">🔐 Login</a>
            <a href="/dashboard">📊 Dashboard</a>
        </div>
        
        <div class="card login-form">
            <h2>Sign In</h2>
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <select name="algorithm">
                    <option value="HS256">HS256 (Symmetric)</option>
                    <option value="RS256">RS256 (Asymmetric)</option>
                </select>
                <button type="submit">Login & Get JWT</button>
            </form>
            
            <div class="warning" style="margin-top: 20px;">
                <strong>💡 Test Credentials:</strong><br>
                • guest / guest (role: guest)<br>
                • user / password123 (role: user)
            </div>
        </div>
    </div>
</body>
</html>
"""

HINTS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Hints - Token Tower</title>
    """ + BASE_STYLE + """
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💡 Attack Hints</h1>
            <p class="subtitle">Guidance for JWT Exploitation</p>
        </div>
        
        <div class="nav">
            <a href="/">🏠 Home</a>
            <a href="/login">🔐 Login</a>
            <a href="/dashboard">📊 Dashboard</a>
        </div>
        
        <div class="card">
            <h2>🔓 Hint 1: Weak Secret Attack</h2>
            <p>The JWT secret might be in common wordlists. Try tools like:</p>
            <div class="code-block">
# Using jwt_tool
python3 jwt_tool.py &lt;token&gt; -C -d wordlist.txt

# Using hashcat
hashcat -a 0 -m 16500 jwt.txt rockyou.txt
            </div>
        </div>
        
        <div class="card">
            <h2>⚡ Hint 2: None Algorithm</h2>
            <p>Some servers accept tokens with algorithm set to "none":</p>
            <div class="code-block">
# Modified header
{"alg": "none", "typ": "JWT"}

# Token format (note trailing dot, no signature)
header.payload.
            </div>
        </div>
        
        <div class="card">
            <h2>🔄 Hint 3: Algorithm Confusion</h2>
            <p>If the server uses RS256, try signing with HS256 using the public key:</p>
            <div class="code-block">
# Get the public key from /public-key endpoint
# Sign with HS256 using the public key as secret
import jwt
token = jwt.encode(payload, public_key_pem, algorithm="HS256")
            </div>
        </div>
        
        <div class="card">
            <h2>💉 Hint 4: JWK Injection</h2>
            <p>Try injecting your own key in the JWT header:</p>
            <div class="code-block">
{
  "alg": "RS256",
  "typ": "JWT",
  "jwk": {
    "kty": "RSA",
    "n": "your_modulus...",
    "e": "AQAB"
  }
}
            </div>
        </div>
        
        <div class="card">
            <h2>📝 Hint 5: Claim Manipulation</h2>
            <p>Change the role claim after bypassing signature:</p>
            <div class="code-block">
# Original payload
{"user": "guest", "role": "guest"}

# Modified payload
{"user": "guest", "role": "admin"}
            </div>
        </div>
    </div>
</body>
</html>
"""

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def home():
    return HOME_PAGE


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return LOGIN_PAGE
    
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    algorithm = request.form.get('algorithm', 'HS256')
    
    # Check credentials
    if username not in USERS or USERS[username]['password'] != password:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>Login Failed</title>""" + BASE_STYLE + """</head>
        <body>
            <div class="container">
                <div class="header"><h1>❌ Login Failed</h1></div>
                <div class="card">
                    <div class="error">Invalid username or password</div>
                    <a href="/login" class="btn">Try Again</a>
                </div>
            </div>
        </body>
        </html>
        """)
    
    user = USERS[username]
    
    # Create JWT payload
    payload = {
        "user": username,
        "user_id": user['id'],
        "role": user['role'],
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    
    # Sign token based on algorithm choice
    if algorithm == 'RS256':
        token = jwt.encode(payload, PRIVATE_KEY_PEM, algorithm='RS256')
    else:
        # VULNERABILITY: Using weak secret
        token = jwt.encode(payload, WEAK_SECRET, algorithm='HS256')
    
    # Create response with JWT cookie
    response = make_response(redirect('/dashboard'))
    response.set_cookie('auth_token', token, httponly=False)  # httponly=False for educational purposes
    response.set_cookie('token_algorithm', algorithm)
    
    return response


@app.route('/logout')
def logout():
    response = make_response(redirect('/'))
    response.delete_cookie('auth_token')
    response.delete_cookie('token_algorithm')
    return response


@app.route('/dashboard')
def dashboard():
    token = request.cookies.get('auth_token')
    
    if not token:
        return redirect('/login')
    
    try:
        # VULNERABILITY: Multiple algorithm vulnerabilities
        data = verify_token_vulnerable(token)
        
        if data is None:
            raise Exception("Token verification failed")
        
        user = data.get('user', 'unknown')
        role = data.get('role', 'guest')
        user_id = data.get('user_id', 0)
        
        # Determine which flags to show based on role and attack method
        flags_earned = []
        attack_method = data.get('attack_method', 'normal')
        
        if role == 'admin':
            flags_earned.append(("Privilege Escalation", FLAGS['privilege_escalation']))
            
            if attack_method == 'none_algorithm':
                flags_earned.append(("None Algorithm", FLAGS['none_algorithm']))
            elif attack_method == 'algorithm_confusion':
                flags_earned.append(("Algorithm Confusion", FLAGS['algorithm_confusion']))
            elif attack_method == 'jwk_injection':
                flags_earned.append(("JWK Injection", FLAGS['jwk_injection']))
            elif attack_method == 'weak_secret':
                flags_earned.append(("Weak Secret", FLAGS['weak_secret']))
            
            if len(flags_earned) >= 2:
                flags_earned.append(("Master Hacker", FLAGS['master']))
        
        # Build flags HTML
        flags_html = ""
        if flags_earned:
            for flag_name, flag_value in flags_earned:
                flags_html += f'<div class="flag">🏆 {flag_name}: {flag_value}</div>'
        
        # Token display
        token_parts = token.split('.')
        if len(token_parts) == 3:
            token_display = f'<span class="jwt-header">{token_parts[0]}</span>.<span class="jwt-payload">{token_parts[1]}</span>.<span class="jwt-signature">{token_parts[2][:20]}...</span>'
        else:
            token_display = token[:50] + "..."
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>Dashboard - Token Tower</title>""" + BASE_STYLE + """</head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Dashboard</h1>
                    <p class="subtitle">Welcome back, {{ user }}!</p>
                </div>
                
                <div class="nav">
                    <a href="/">🏠 Home</a>
                    <a href="/dashboard">📊 Dashboard</a>
                    <a href="/api/docs">📚 API Docs</a>
                    <a href="/logout">🚪 Logout</a>
                </div>
                
                <div class="dashboard-grid">
                    <div class="stat-card">
                        <div class="value">{{ user }}</div>
                        <div class="label">Username</div>
                    </div>
                    <div class="stat-card">
                        <div class="value">{{ role }}</div>
                        <div class="label">Role</div>
                    </div>
                    <div class="stat-card">
                        <div class="value">{{ user_id }}</div>
                        <div class="label">User ID</div>
                    </div>
                </div>
                
                {% if flags_html %}
                <div class="card">
                    <h2>🏆 Flags Captured!</h2>
                    {{ flags_html | safe }}
                </div>
                {% endif %}
                
                {% if role != 'admin' %}
                <div class="card">
                    <h2>🔒 Admin Area</h2>
                    <div class="warning">
                        You do not have admin privileges. Can you find a way to escalate?
                    </div>
                </div>
                {% else %}
                <div class="card">
                    <h2>👑 Admin Panel</h2>
                    <div class="success">
                        Welcome, Admin! You have full access to the system.
                    </div>
                    <table>
                        <tr><th>User</th><th>Role</th><th>ID</th></tr>
                        <tr><td>admin</td><td>admin</td><td>1</td></tr>
                        <tr><td>guest</td><td>guest</td><td>2</td></tr>
                        <tr><td>user</td><td>user</td><td>3</td></tr>
                    </table>
                </div>
                {% endif %}
                
                <div class="card">
                    <h2>🎫 Your JWT Token</h2>
                    <div class="code-block jwt-parts">
                        {{ token_display | safe }}
                    </div>
                    <p style="margin-top: 10px; color: #888;">
                        Decode this token at <a href="https://jwt.io" target="_blank" style="color: #00d9ff;">jwt.io</a>
                    </p>
                </div>
                
                <div class="card">
                    <h2>🔍 Decoded Payload</h2>
                    <div class="code-block">{{ payload | safe }}</div>
                </div>
            </div>
        </body>
        </html>
        """, user=user, role=role, user_id=user_id, flags_html=flags_html,
             token_display=token_display, payload=json.dumps(data, indent=2, default=str))
        
    except Exception as e:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head><title>Error - Token Tower</title>""" + BASE_STYLE + """</head>
        <body>
            <div class="container">
                <div class="header"><h1>❌ Token Error</h1></div>
                <div class="card">
                    <div class="error">
                        <strong>Token Verification Failed:</strong><br>
                        {{ error }}
                    </div>
                    <a href="/login" class="btn">Login Again</a>
                </div>
            </div>
        </body>
        </html>
        """, error=str(e))


@app.route('/public-key')
def public_key():
    """Expose public key - needed for algorithm confusion attacks"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>Public Key - Token Tower</title>""" + BASE_STYLE + """</head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔑 Public Key</h1>
                <p class="subtitle">RSA Public Key for RS256 Verification</p>
            </div>
            
            <div class="nav">
                <a href="/">🏠 Home</a>
                <a href="/login">🔐 Login</a>
                <a href="/dashboard">📊 Dashboard</a>
            </div>
            
            <div class="card">
                <h2>PEM Format</h2>
                <div class="code-block">{{ public_key }}</div>
            </div>
            
            <div class="warning">
                <strong>💡 Hint:</strong> In algorithm confusion attacks, the public key can be used as an HMAC secret when the server doesn't properly validate the algorithm.
            </div>
        </div>
    </body>
    </html>
    """, public_key=PUBLIC_KEY_PEM)


@app.route('/hints')
def hints():
    return HINTS_PAGE


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/docs')
def api_docs():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head><title>API Documentation - Token Tower</title>""" + BASE_STYLE + """</head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 API Documentation</h1>
                <p class="subtitle">REST API Endpoints</p>
            </div>
            
            <div class="nav">
                <a href="/">🏠 Home</a>
                <a href="/dashboard">📊 Dashboard</a>
            </div>
            
            <div class="card">
                <h2>🔐 Authentication</h2>
                <table>
                    <tr><th>Endpoint</th><th>Method</th><th>Description</th></tr>
                    <tr><td>/api/auth</td><td>POST</td><td>Authenticate and receive JWT</td></tr>
                    <tr><td>/api/verify</td><td>POST</td><td>Verify a JWT token</td></tr>
                    <tr><td>/api/refresh</td><td>POST</td><td>Refresh JWT token</td></tr>
                </table>
            </div>
            
            <div class="card">
                <h2>🔒 Protected Resources</h2>
                <table>
                    <tr><th>Endpoint</th><th>Method</th><th>Required Role</th></tr>
                    <tr><td>/api/user/profile</td><td>GET</td><td>Any authenticated</td></tr>
                    <tr><td>/api/admin/users</td><td>GET</td><td>admin</td></tr>
                    <tr><td>/api/admin/flag</td><td>GET</td><td>admin</td></tr>
                </table>
            </div>
            
            <div class="card">
                <h2>📝 Example: Authenticate</h2>
                <div class="code-block">
curl -X POST http://localhost:5020/api/auth \\
  -H "Content-Type: application/json" \\
  -d '{"username": "guest", "password": "guest"}'
                </div>
            </div>
            
            <div class="card">
                <h2>📝 Example: Access Protected Resource</h2>
                <div class="code-block">
curl http://localhost:5020/api/admin/users \\
  -H "Authorization: Bearer &lt;your_jwt_token&gt;"
                </div>
            </div>
        </div>
    </body>
    </html>
    """)


@app.route('/api/auth', methods=['POST'])
def api_auth():
    """API authentication endpoint"""
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    algorithm = data.get('algorithm', 'HS256')
    
    if username not in USERS or USERS[username]['password'] != password:
        return jsonify({"error": "Invalid credentials"}), 401
    
    user = USERS[username]
    payload = {
        "user": username,
        "user_id": user['id'],
        "role": user['role'],
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    
    if algorithm == 'RS256':
        token = jwt.encode(payload, PRIVATE_KEY_PEM, algorithm='RS256')
    else:
        token = jwt.encode(payload, WEAK_SECRET, algorithm='HS256')
    
    return jsonify({
        "success": True,
        "token": token,
        "algorithm": algorithm,
        "expires_in": 3600
    })


@app.route('/api/verify', methods=['POST'])
def api_verify():
    """Verify a JWT token"""
    data = request.get_json() or {}
    token = data.get('token', '')
    
    if not token:
        return jsonify({"error": "No token provided"}), 400
    
    try:
        payload = verify_token_vulnerable(token)
        if payload:
            return jsonify({"valid": True, "payload": payload})
        else:
            return jsonify({"valid": False, "error": "Verification failed"}), 401
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 401


@app.route('/api/user/profile')
def api_user_profile():
    """Get user profile - requires authentication"""
    token = get_token_from_request()
    
    if not token:
        return jsonify({"error": "No authorization token provided"}), 401
    
    try:
        payload = verify_token_vulnerable(token)
        if payload:
            return jsonify({
                "user": payload.get('user'),
                "role": payload.get('role'),
                "user_id": payload.get('user_id')
            })
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401


@app.route('/api/admin/users')
def api_admin_users():
    """Get all users - requires admin role"""
    token = get_token_from_request()
    
    if not token:
        return jsonify({"error": "No authorization token provided"}), 401
    
    try:
        payload = verify_token_vulnerable(token)
        if not payload:
            return jsonify({"error": "Invalid token"}), 401
        
        if payload.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        # Return users (without passwords)
        users_list = [
            {"username": u, "role": d['role'], "id": d['id']}
            for u, d in USERS.items()
        ]
        
        return jsonify({"users": users_list})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 401


@app.route('/api/admin/flag')
def api_admin_flag():
    """Get the admin flag - requires admin role"""
    token = get_token_from_request()
    
    if not token:
        return jsonify({"error": "No authorization token provided"}), 401
    
    try:
        payload = verify_token_vulnerable(token)
        if not payload:
            return jsonify({"error": "Invalid token"}), 401
        
        if payload.get('role') != 'admin':
            return jsonify({"error": "Admin access required", "your_role": payload.get('role')}), 403
        
        return jsonify({
            "message": "Congratulations! You've gained admin access!",
            "flag": FLAGS['privilege_escalation'],
            "attack_method": payload.get('attack_method', 'unknown')
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 401


@app.route('/.well-known/jwks.json')
def jwks():
    """JWKS endpoint for key discovery"""
    # Get public key numbers
    public_numbers = PUBLIC_KEY.public_numbers()
    
    # Convert to base64url encoding
    def int_to_base64url(n, length=None):
        if length is None:
            length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(length, 'big')).decode('utf-8').rstrip('=')
    
    jwks_data = {
        "keys": [{
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": "token-tower-key-1",
            "n": int_to_base64url(public_numbers.n),
            "e": int_to_base64url(public_numbers.e)
        }]
    }
    
    return jsonify(jwks_data)


# ============================================================================
# VULNERABLE TOKEN VERIFICATION (Intentional Vulnerabilities)
# ============================================================================

def verify_token_vulnerable(token):
    """
    VULNERABLE token verification function.
    Contains multiple intentional security flaws for educational purposes.
    """
    try:
        # Decode header without verification first
        try:
            header = jwt.get_unverified_header(token)
        except:
            return None
        
        algorithm = header.get('alg', 'HS256')
        
        # VULNERABILITY 1: Accept "none" algorithm
        if algorithm.lower() == 'none':
            try:
                # Decode without verification
                payload = jwt.decode(token, options={"verify_signature": False})
                payload['attack_method'] = 'none_algorithm'
                return payload
            except:
                return None
        
        # VULNERABILITY 2: JWK Header Injection
        if 'jwk' in header:
            try:
                # Dangerous: Trust the key from the header
                jwk_data = header['jwk']
                # Build public key from JWK
                from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
                n = int.from_bytes(base64.urlsafe_b64decode(jwk_data['n'] + '=='), 'big')
                e = int.from_bytes(base64.urlsafe_b64decode(jwk_data['e'] + '=='), 'big')
                public_numbers = RSAPublicNumbers(e, n)
                injected_key = public_numbers.public_key(default_backend())
                injected_key_pem = injected_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                payload = jwt.decode(token, injected_key_pem, algorithms=['RS256'])
                payload['attack_method'] = 'jwk_injection'
                return payload
            except Exception as e:
                pass  # Fall through to other methods
        
        # VULNERABILITY 3: Algorithm Confusion (RS256 to HS256)
        # If header says HS256, use the secret; if RS256, use public key
        # But vulnerability: if someone changes RS256 to HS256 and signs with public key...
        if algorithm == 'HS256':
            try:
                payload = jwt.decode(token, WEAK_SECRET, algorithms=['HS256'])
                
                # Check if this might be algorithm confusion (public key used as HMAC secret)
                try:
                    jwt.decode(token, PUBLIC_KEY_PEM, algorithms=['HS256'])
                    payload['attack_method'] = 'algorithm_confusion'
                except:
                    payload['attack_method'] = 'weak_secret'
                
                return payload
            except jwt.InvalidSignatureError:
                # Maybe they signed with the public key (algorithm confusion)
                try:
                    payload = jwt.decode(token, PUBLIC_KEY_PEM, algorithms=['HS256'])
                    payload['attack_method'] = 'algorithm_confusion'
                    return payload
                except:
                    return None
            except:
                return None
        
        elif algorithm == 'RS256':
            try:
                payload = jwt.decode(token, PUBLIC_KEY_PEM, algorithms=['RS256'])
                payload['attack_method'] = 'normal'
                return payload
            except:
                return None
        
        else:
            return None
            
    except Exception as e:
        return None


def get_token_from_request():
    """Extract JWT from Authorization header or cookie"""
    # Check Authorization header first
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # Fall back to cookie
    return request.cookies.get('auth_token')


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🗼 Token Tower - JWT Vulnerability Lab")
    print("=" * 60)
    print("⚠️  WARNING: This application contains intentional vulnerabilities!")
    print("📚 Educational use only - WebSploit Labs")
    print("=" * 60)
    print("\n🎯 Vulnerabilities:")
    print("   • Weak signing secret (crackable)")
    print("   • None algorithm attack")
    print("   • Algorithm confusion (RS256 → HS256)")
    print("   • JWK header injection")
    print("   • Claim manipulation")
    print("\n🔑 Test Credentials:")
    print("   • guest / guest (role: guest)")
    print("   • user / password123 (role: user)")
    print("\n🌐 Access: http://localhost:5020")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5020, debug=False)
