#!/usr/bin/env python3
"""
WebSploit Labs - SSRF Vulnerable Application
Created for educational purposes by Omar Santos
This application demonstrates various SSRF vulnerabilities
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

# HTML template for the main page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSploit Labs - URL Fetcher Service</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .service { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff; }
        input[type="text"] { width: 70%; padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { background: #e9ecef; padding: 15px; margin-top: 10px; border-radius: 4px; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 WebSploit Labs - URL Fetcher Service</h1>
        <div class="warning">
            ⚠️ <strong>Educational Environment:</strong> This application contains intentional vulnerabilities for learning purposes.
        </div>
        
        <div class="service">
            <h3>📡 Web Content Fetcher</h3>
            <p>Fetch content from any URL for analysis:</p>
            <form method="POST" action="/fetch">
                <input type="text" name="url" placeholder="https://example.com" required>
                <button type="submit">Fetch Content</button>
            </form>
        </div>
        
        <div class="service">
            <h3>🔍 Website Screenshot Service</h3>
            <p>Generate screenshots of websites:</p>
            <form method="POST" action="/screenshot">
                <input type="text" name="url" placeholder="https://example.com" required>
                <button type="submit">Take Screenshot</button>
            </form>
        </div>
        
        <div class="service">
            <h3>🌐 Webhook Tester</h3>
            <p>Test webhook endpoints by sending POST requests:</p>
            <form method="POST" action="/webhook">
                <input type="text" name="webhook_url" placeholder="https://webhook.site/your-uuid" required>
                <input type="text" name="data" placeholder="Test data to send" required>
                <button type="submit">Send Webhook</button>
            </form>
        </div>
        
        <div class="service">
            <h3>📊 URL Metadata Analyzer</h3>
            <p>Analyze URL metadata and headers:</p>
            <form method="POST" action="/analyze">
                <input type="text" name="target_url" placeholder="https://example.com" required>
                <button type="submit">Analyze URL</button>
            </form>
        </div>
        
        <div class="service">
            <h3>🔗 Link Validator</h3>
            <p>Validate if links are accessible:</p>
            <form method="POST" action="/validate">
                <input type="text" name="link" placeholder="https://example.com" required>
                <button type="submit">Validate Link</button>
            </form>
        </div>
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
        return "Please provide a URL", 400
    
    try:
        # VULNERABILITY: No URL validation or filtering
        response = make_request(url)
        if response:
            content = f"Status Code: {response.status_code}\n"
            content += f"Headers: {dict(response.headers)}\n\n"
            content += f"Content (first 2000 chars):\n{response.text[:2000]}"
            return render_template_string(f"""
                <h2>Fetch Results for: {url}</h2>
                <div class="result">{content}</div>
                <a href="/">← Back</a>
            """)
        else:
            return "Failed to fetch URL", 500
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/screenshot', methods=['POST'])
def screenshot_service():
    """Vulnerable endpoint #2: SSRF through screenshot service simulation"""
    url = request.form.get('url', '')
    
    if not url:
        return "Please provide a URL", 400
    
    try:
        # VULNERABILITY: Simulating a screenshot service that makes requests
        response = make_request(url)
        if response:
            # Simulate screenshot generation by fetching the page
            result = f"Screenshot service accessed: {url}\n"
            result += f"Page title extraction attempt...\n"
            result += f"Status: {response.status_code}\n"
            result += f"Content-Type: {response.headers.get('content-type', 'unknown')}\n"
            result += f"Content length: {len(response.text)} characters\n"
            
            # Try to extract title
            if '<title>' in response.text.lower():
                start = response.text.lower().find('<title>') + 7
                end = response.text.lower().find('</title>', start)
                if end > start:
                    title = response.text[start:end]
                    result += f"Extracted title: {title[:100]}\n"
            
            return render_template_string(f"""
                <h2>Screenshot Service Results</h2>
                <div class="result">{result}</div>
                <a href="/">← Back</a>
            """)
        else:
            return "Failed to access URL for screenshot", 500
    except Exception as e:
        return f"Screenshot service error: {str(e)}", 500

@app.route('/webhook', methods=['POST'])
def webhook_tester():
    """Vulnerable endpoint #3: SSRF through webhook testing"""
    webhook_url = request.form.get('webhook_url', '')
    data = request.form.get('data', 'test data')
    
    if not webhook_url:
        return "Please provide a webhook URL", 400
    
    try:
        # VULNERABILITY: No validation of webhook URL
        payload = {'message': data, 'timestamp': '2024-01-01T00:00:00Z'}
        response = make_request(webhook_url, method='POST', data=payload)
        
        if response:
            result = f"Webhook sent to: {webhook_url}\n"
            result += f"Response status: {response.status_code}\n"
            result += f"Response headers: {dict(response.headers)}\n"
            result += f"Response body: {response.text[:500]}"
            
            return render_template_string(f"""
                <h2>Webhook Test Results</h2>
                <div class="result">{result}</div>
                <a href="/">← Back</a>
            """)
        else:
            return "Failed to send webhook", 500
    except Exception as e:
        return f"Webhook error: {str(e)}", 500

@app.route('/analyze', methods=['POST'])
def analyze_url():
    """Vulnerable endpoint #4: SSRF through URL analysis"""
    target_url = request.form.get('target_url', '')
    
    if not target_url:
        return "Please provide a target URL", 400
    
    try:
        # VULNERABILITY: Multiple requests to analyze URL
        result = f"Analyzing URL: {target_url}\n\n"
        
        # HEAD request to get headers
        head_response = make_request(target_url, method='HEAD')
        if head_response:
            result += f"HEAD Request Results:\n"
            result += f"Status: {head_response.status_code}\n"
            result += f"Headers: {dict(head_response.headers)}\n\n"
        
        # GET request to analyze content
        get_response = make_request(target_url)
        if get_response:
            result += f"GET Request Results:\n"
            result += f"Content-Length: {len(get_response.text)}\n"
            result += f"Apparent encoding: {get_response.encoding}\n"
            
            # Analyze for common elements
            content_lower = get_response.text.lower()
            result += f"Contains forms: {'Yes' if '<form' in content_lower else 'No'}\n"
            result += f"Contains scripts: {'Yes' if '<script' in content_lower else 'No'}\n"
            result += f"Contains images: {'Yes' if '<img' in content_lower else 'No'}\n"
        
        return render_template_string(f"""
            <h2>URL Analysis Results</h2>
            <div class="result">{result}</div>
            <a href="/">← Back</a>
        """)
    except Exception as e:
        return f"Analysis error: {str(e)}", 500

@app.route('/validate', methods=['POST'])
def validate_link():
    """Vulnerable endpoint #5: SSRF through link validation"""
    link = request.form.get('link', '')
    
    if not link:
        return "Please provide a link", 400
    
    try:
        # VULNERABILITY: Link validation that makes actual requests
        result = f"Validating link: {link}\n\n"
        
        # Check if URL is reachable
        response = make_request(link, timeout=5)
        if response:
            result += f"✓ Link is accessible\n"
            result += f"Status Code: {response.status_code}\n"
            result += f"Final URL (after redirects): {response.url}\n"
            result += f"Server: {response.headers.get('server', 'Unknown')}\n"
            result += f"Content-Type: {response.headers.get('content-type', 'Unknown')}\n"
            
            # Additional "validation" checks
            if response.status_code == 200:
                result += f"✓ Returns successful response\n"
            if 'text/html' in response.headers.get('content-type', ''):
                result += f"✓ Appears to be a valid webpage\n"
                
        else:
            result += f"✗ Link is not accessible or timed out\n"
        
        return render_template_string(f"""
            <h2>Link Validation Results</h2>
            <div class="result">{result}</div>
            <a href="/">← Back</a>
        """)
    except Exception as e:
        return f"Validation error: {str(e)}", 500

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
    print("🚀 WebSploit Labs - SSRF Vulnerable Application")
    print("⚠️  WARNING: This application contains intentional vulnerabilities!")
    print("📚 Educational use only - Created by Omar Santos")
    print("🌐 Access the application at: http://localhost:5012")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5012, debug=True)