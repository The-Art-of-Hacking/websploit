#!/usr/bin/env python3
"""
NetProbe Diagnostics Suite
Internal network analysis and validation tools.
"""

from flask import Flask, request, render_template_string, jsonify
import requests
import urllib.parse
import socket
import subprocess
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

# Modern Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetProbe Diagnostics Suite</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #0f172a;
            --secondary: #334155;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --border: #e2e8f0;
        }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 0;
            line-height: 1.5;
        }
        .navbar {
            background-color: var(--card-bg);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .brand {
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--primary);
        }
        .brand-icon {
            background: var(--accent);
            color: white;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
            font-weight: bold;
        }
        .container {
            max-width: 1100px;
            margin: 3rem auto;
            padding: 0 1.5rem;
        }
        .dashboard-header {
            margin-bottom: 2.5rem;
            text-align: center;
        }
        .dashboard-header h1 {
            font-size: 2rem;
            margin: 0;
            font-weight: 700;
            letter-spacing: -0.025em;
            color: var(--primary);
        }
        .dashboard-header p {
            color: #64748b;
            margin-top: 0.75rem;
            font-size: 1.1rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 1.5rem;
        }
        .card {
            background: var(--card-bg);
            border-radius: 0.75rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1);
            padding: 1.75rem;
            border: 1px solid var(--border);
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border-color: #cbd5e1;
        }
        .card h3 {
            margin-top: 0;
            color: var(--primary);
            font-size: 1.15rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }
        .card p {
            font-size: 0.925rem;
            color: #64748b;
            margin-bottom: 1.5rem;
            flex-grow: 1;
        }
        form {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-top: auto;
        }
        input[type="text"] {
            padding: 0.75rem;
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            font-size: 0.9rem;
            width: 100%;
            box-sizing: border-box;
            transition: all 0.2s;
            background: #f8fafc;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: var(--accent);
            background: white;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        button {
            background-color: var(--primary);
            color: white;
            padding: 0.75rem;
            border: none;
            border-radius: 0.5rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
            width: 100%;
            font-size: 0.9rem;
        }
        button:hover {
            background-color: var(--accent);
        }
        footer {
            text-align: center;
            margin-top: 5rem;
            padding: 2rem;
            color: #94a3b8;
            font-size: 0.875rem;
            border-top: 1px solid var(--border);
            background: white;
        }
        .tag {
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 4px;
            background: #e2e8f0;
            color: #64748b;
            font-weight: normal;
            margin-left: auto;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="brand">
            <div class="brand-icon">NP</div>
            NetProbe Enterprise
        </div>
        <div style="font-size: 0.875rem; color: #64748b;">v2.4.1</div>
    </div>

    <div class="container">
        <div class="dashboard-header">
            <h1>Diagnostic Toolkit</h1>
            <p>Secure network analysis and connectivity validation suite.</p>
        </div>
        
        <div class="grid">
            <!-- Fetcher -->
            <div class="card">
                <h3>📡 Content Fetcher <span class="tag">HTTP/1.1</span></h3>
                <p>Retrieve raw content from internal or external endpoints to verify availability and integrity.</p>
                <form method="POST" action="/fetch">
                    <input type="text" name="url" placeholder="http://internal-service:8080" required>
                    <button type="submit">Fetch Resource</button>
                </form>
            </div>
            
            <!-- Screenshot -->
            <div class="card">
                <h3>📸 Site Visualizer <span class="tag">BETA</span></h3>
                <p>Generate a metadata snapshot and visual preview structure of target web properties.</p>
                <form method="POST" action="/screenshot">
                    <input type="text" name="url" placeholder="https://example.com" required>
                    <button type="submit">Generate Snapshot</button>
                </form>
            </div>
            
            <!-- Webhook -->
            <div class="card">
                <h3>🔗 Webhook Tester <span class="tag">POST</span></h3>
                <p>Test webhook integrations by dispatching custom payloads to specified endpoints.</p>
                <form method="POST" action="/webhook">
                    <input type="text" name="webhook_url" placeholder="Destination URL" required>
                    <input type="text" name="data" placeholder="Payload (JSON/Text)" required>
                    <button type="submit">Dispatch Event</button>
                </form>
            </div>
            
            <!-- Analyzer -->
            <div class="card">
                <h3>📊 Header Analyzer <span class="tag">Deep Scan</span></h3>
                <p>Inspect HTTP headers, server fingerprints, and structural elements of remote resources.</p>
                <form method="POST" action="/analyze">
                    <input type="text" name="target_url" placeholder="https://api.example.com" required>
                    <button type="submit">Analyze Headers</button>
                </form>
            </div>
            
            <!-- Validator -->
            <div class="card">
                <h3>✅ Link Validator <span class="tag">Quick</span></h3>
                <p>Validate upstream link status, redirect chains, and server reachability metrics.</p>
                <form method="POST" action="/validate">
                    <input type="text" name="link" placeholder="Link to validate" required>
                    <button type="submit">Check Connectivity</button>
                </form>
            </div>
        </div>
    </div>

    <footer>
        &copy; 2023 NetProbe Systems Inc. <br> 
        Authorized Personnel Only. Access Monitored.
    </footer>
</body>
</html>
"""

# Template for Results
RESULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diagnostic Result - NetProbe</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #0f172a;
            --accent: #3b82f6;
            --bg: #f8fafc;
            --text: #1e293b;
            --border: #e2e8f0;
        }}
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 2rem;
            display: flex;
            justify-content: center;
            min-height: 100vh;
        }}
        .container {{
            background: white;
            padding: 2.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            max-width: 900px;
            width: 100%;
            height: fit-content;
            border: 1px solid var(--border);
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        h2 {{ 
            margin: 0; 
            color: var(--primary); 
            font-size: 1.5rem; 
            display: flex; 
            align-items: center; 
            gap: 12px; 
        }}
        .output {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 1.5rem;
            border-radius: 0.5rem;
            font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
            font-size: 0.9rem;
            white-space: pre-wrap;
            overflow-x: auto;
            margin: 1.5rem 0;
            border: 1px solid #334155;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            background-color: var(--primary);
            color: white;
            padding: 0.75rem 1.5rem;
            text-decoration: none;
            border-radius: 0.5rem;
            font-weight: 500;
            transition: background-color 0.2s;
            font-size: 0.9rem;
        }}
        .btn:hover {{ background-color: var(--accent); }}
        .status {{
            font-size: 0.875rem;
            color: #64748b;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>{title}</h2>
            <span class="status">STATUS: COMPLETE</span>
        </div>
        <div class="output">{content}</div>
        <a href="/" class="btn">← Return to Dashboard</a>
    </div>
</body>
</html>
"""

def make_request(url, method='GET', data=None, timeout=10):
    """Make HTTP request with basic retry logic"""
    session = requests.Session()
    retry_strategy = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    try:
        if method.upper() == 'POST':
            response = session.post(url, data=data, timeout=timeout, allow_redirects=True)
        else:
            response = session.get(url, timeout=timeout, allow_redirects=True)
        return response
    except Exception as e:
        return None

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/fetch', methods=['POST'])
def fetch_url():
    """Vulnerable endpoint #1: Basic SSRF through URL fetching"""
    url = request.form.get('url', '')
    
    if not url:
        return render_template_string(RESULT_TEMPLATE.format(title="Error", content="Please provide a valid URL."))
    
    try:
        # VULNERABILITY: No URL validation or filtering
        response = make_request(url)
        if response:
            content = f"Target: {url}\n"
            content += f"Status: {response.status_code} {response.reason}\n"
            content += f"Headers: {dict(response.headers)}\n\n"
            content += f"--- Body Preview (First 2000 bytes) ---\n{response.text[:2000]}"
            
            return render_template_string(RESULT_TEMPLATE.format(
                title="Fetch Result", 
                content=content
            ))
        else:
            return render_template_string(RESULT_TEMPLATE.format(title="Request Failed", content="Unable to reach the target host. The host may be down or unreachable."))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(title="System Error", content="An internal error occurred while processing the request."))

@app.route('/screenshot', methods=['POST'])
def screenshot_service():
    """Vulnerable endpoint #2: SSRF through screenshot service simulation"""
    url = request.form.get('url', '')
    
    if not url:
        return render_template_string(RESULT_TEMPLATE.format(title="Error", content="Please provide a valid URL."))
    
    try:
        # VULNERABILITY: Simulating a screenshot service that makes requests
        response = make_request(url)
        if response:
            # Simulate screenshot generation by fetching the page
            result = f"Target: {url}\n"
            result += f"Action: Generating viewport snapshot...\n"
            result += f"Status: {response.status_code}\n"
            result += f"MIME Type: {response.headers.get('content-type', 'unknown')}\n"
            result += f"Size: {len(response.text)} bytes\n"
            
            # Try to extract title
            if '<title>' in response.text.lower():
                start = response.text.lower().find('<title>') + 7
                end = response.text.lower().find('</title>', start)
                if end > start:
                    title = response.text[start:end]
                    result += f"Page Title: {title[:100]}\n"
            
            result += "\n[Snapshot Metadata Generated Successfully]"
            
            return render_template_string(RESULT_TEMPLATE.format(
                title="Snapshot Result",
                content=result
            ))
        else:
            return render_template_string(RESULT_TEMPLATE.format(title="Snapshot Failed", content="Unable to access target URL for rendering."))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(title="Service Error", content="Snapshot service encountered an unexpected error."))

@app.route('/webhook', methods=['POST'])
def webhook_tester():
    """Vulnerable endpoint #3: SSRF through webhook testing"""
    webhook_url = request.form.get('webhook_url', '')
    data = request.form.get('data', 'test data')
    
    if not webhook_url:
        return render_template_string(RESULT_TEMPLATE.format(title="Error", content="Webhook URL required."))
    
    try:
        # VULNERABILITY: No validation of webhook URL
        payload = {'message': data, 'timestamp': '2024-01-01T00:00:00Z'}
        response = make_request(webhook_url, method='POST', data=payload)
        
        if response:
            result = f"Dispatch Target: {webhook_url}\n"
            result += f"Delivery Status: {response.status_code}\n"
            result += f"Remote Headers: {dict(response.headers)}\n"
            result += f"Remote Response Body:\n{response.text[:500]}"
            
            return render_template_string(RESULT_TEMPLATE.format(
                title="Webhook Delivery Report",
                content=result
            ))
        else:
            return render_template_string(RESULT_TEMPLATE.format(title="Delivery Failed", content="Could not connect to the webhook listener."))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(title="System Error", content="Webhook dispatch service error."))

@app.route('/analyze', methods=['POST'])
def analyze_url():
    """Vulnerable endpoint #4: SSRF through URL analysis"""
    target_url = request.form.get('target_url', '')
    
    if not target_url:
        return render_template_string(RESULT_TEMPLATE.format(title="Error", content="Target URL required."))
    
    try:
        # VULNERABILITY: Multiple requests to analyze URL
        result = f"Analysis Target: {target_url}\n\n"
        
        # HEAD request to get headers
        head_response = make_request(target_url, method='HEAD')
        if head_response:
            result += f"[HEAD Probe]\n"
            result += f"Status: {head_response.status_code}\n"
            result += f"Headers: {dict(head_response.headers)}\n\n"
        
        # GET request to analyze content
        get_response = make_request(target_url)
        if get_response:
            result += f"[Content Scan]\n"
            result += f"Size: {len(get_response.text)} bytes\n"
            result += f"Encoding: {get_response.encoding}\n"
            
            # Analyze for common elements
            content_lower = get_response.text.lower()
            result += f"Detected Forms: {'Yes' if '<form' in content_lower else 'No'}\n"
            result += f"Detected Scripts: {'Yes' if '<script' in content_lower else 'No'}\n"
            result += f"Detected Images: {'Yes' if '<img' in content_lower else 'No'}\n"
        
        return render_template_string(RESULT_TEMPLATE.format(
            title="Analysis Report",
            content=result
        ))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(title="Analysis Error", content="Failed to complete the analysis sequence."))

@app.route('/validate', methods=['POST'])
def validate_link():
    """Vulnerable endpoint #5: SSRF through link validation"""
    link = request.form.get('link', '')
    
    if not link:
        return render_template_string(RESULT_TEMPLATE.format(title="Error", content="Link required for validation."))
    
    try:
        # VULNERABILITY: Link validation that makes actual requests
        result = f"Validating: {link}\n\n"
        
        # Check if URL is reachable
        response = make_request(link, timeout=5)
        if response:
            result += f"✓ Connectivity Confirmed\n"
            result += f"Status Code: {response.status_code}\n"
            result += f"Resolution URL: {response.url}\n"
            result += f"Server Header: {response.headers.get('server', 'Unknown')}\n"
            result += f"Content-Type: {response.headers.get('content-type', 'Unknown')}\n"
            
            # Additional "validation" checks
            if response.status_code == 200:
                result += f"✓ Upstream returned healthy status (200)\n"
            if 'text/html' in response.headers.get('content-type', ''):
                result += f"✓ Content identified as web document\n"
                
        else:
            result += f"✗ Link Unreachable (Connection Timeout or Refused)\n"
        
        return render_template_string(RESULT_TEMPLATE.format(
            title="Validation Output",
            content=result
        ))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(title="System Error", content="Validation process terminated unexpectedly."))

# Additional endpoint for advanced SSRF testing
@app.route('/api/proxy', methods=['GET', 'POST'])
def api_proxy():
    """Vulnerable API endpoint for proxy functionality"""
    target = request.args.get('url') or request.form.get('url')
    
    if not target:
        return jsonify({'error': 'URL parameter required'}), 400
    
    try:
        response = make_request(target)
        if response:
            return jsonify({
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text[:1000],  # Limit content for API response
                'url': response.url
            })
        else:
            return jsonify({'error': 'Failed to fetch URL'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint that could be abused
@app.route('/health')
def health_check():
    """Health check endpoint that tests connectivity"""
    test_url = request.args.get('test_url', 'http://localhost:5000/')
    
    try:
        response = make_request(test_url, timeout=3)
        if response and response.status_code == 200:
            return jsonify({'status': 'healthy', 'test_url': test_url})
        else:
            return jsonify({'status': 'unhealthy', 'test_url': test_url}), 503
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5012, debug=True)
