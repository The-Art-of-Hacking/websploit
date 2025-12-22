#!/usr/bin/env python3
"""
XXE (XML External Entity) Vulnerable Application
Instructor: Omar Santos (@santosomar)

This is an intentionally vulnerable application for educational purposes.
DO NOT use in production environments.
"""

from flask import Flask, request, render_template_string, jsonify
from lxml import etree
import xml.etree.ElementTree as ET
import io
import os

app = Flask(__name__)

# Simulated internal files for XXE demonstration
INTERNAL_FILES = {
    '/app/config/database.conf': '''# Database Configuration
DB_HOST=internal-db.secretcorp.local
DB_PORT=5432
DB_USER=admin
DB_PASS=Sup3rS3cr3tP@ssw0rd!
DB_NAME=production_data
''',
    '/app/secrets/api_keys.txt': '''# API Keys - CONFIDENTIAL
STRIPE_SECRET_KEY=sk_test_FAKE_KEY_FOR_DEMO_ONLY_1234567890
AWS_ACCESS_KEY_ID=FAKE_AWS_KEY_FOR_DEMO_ONLY
AWS_SECRET_ACCESS_KEY=FAKE_AWS_SECRET_FOR_DEMO_ONLY_1234567890
GITHUB_TOKEN=FAKE_GITHUB_TOKEN_FOR_DEMO_ONLY
''',
    '/app/users/employees.xml': '''<?xml version="1.0"?>
<employees>
    <employee id="1">
        <name>Alice Johnson</name>
        <role>System Administrator</role>
        <ssn>123-45-6789</ssn>
    </employee>
    <employee id="2">
        <name>Bob Smith</name>
        <role>Database Admin</role>
        <ssn>987-65-4321</ssn>
    </employee>
</employees>
''',
}

# Create the simulated files on startup
def create_internal_files():
    for filepath, content in INTERNAL_FILES.items():
        dirpath = os.path.dirname(filepath)
        os.makedirs(dirpath, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(content)

# HTML Template - Modern Dark Theme
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataVault XML Gateway</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #0a0e17;
            --bg-surface: #111827;
            --bg-elevated: #1f2937;
            --accent-primary: #10b981;
            --accent-secondary: #06d6a0;
            --accent-warning: #f59e0b;
            --accent-danger: #ef4444;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --border: #374151;
            --glow: rgba(16, 185, 129, 0.3);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-deep);
            color: var(--text-primary);
            min-height: 100vh;
            background-image: 
                radial-gradient(ellipse at top, rgba(16, 185, 129, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at bottom right, rgba(6, 214, 160, 0.05) 0%, transparent 50%);
        }
        
        .navbar {
            background: rgba(17, 24, 39, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .brand {
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--text-primary);
        }
        
        .brand-icon {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            font-weight: bold;
            font-size: 0.9rem;
            box-shadow: 0 0 20px var(--glow);
        }
        
        .status-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            padding: 4px 10px;
            border-radius: 4px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-primary);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 3rem 1.5rem;
        }
        
        .header {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
            background: linear-gradient(135deg, var(--text-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            color: var(--text-secondary);
            font-size: 1.1rem;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 1.5rem;
        }
        
        .card {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.75rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .card:hover {
            border-color: var(--accent-primary);
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3), 0 0 30px var(--glow);
        }
        
        .card:hover::before {
            opacity: 1;
        }
        
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }
        
        .card h3 {
            font-size: 1.15rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .card-icon {
            font-size: 1.5rem;
        }
        
        .tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.65rem;
            padding: 3px 8px;
            border-radius: 4px;
            background: var(--bg-elevated);
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .tag.warning {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-warning);
        }
        
        .card p {
            color: var(--text-secondary);
            font-size: 0.9rem;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        
        form {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        textarea, input[type="text"] {
            font-family: 'JetBrains Mono', monospace;
            background: var(--bg-deep);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            color: var(--text-primary);
            font-size: 0.85rem;
            resize: vertical;
            transition: all 0.2s ease;
        }
        
        textarea {
            min-height: 120px;
        }
        
        textarea:focus, input[type="text"]:focus {
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px var(--glow);
        }
        
        textarea::placeholder, input[type="text"]::placeholder {
            color: var(--text-muted);
        }
        
        button {
            font-family: 'Space Grotesk', sans-serif;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: var(--bg-deep);
            border: none;
            padding: 0.875rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px var(--glow);
        }
        
        .info-panel {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        
        .info-panel h4 {
            color: var(--accent-primary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 1rem;
        }
        
        .endpoint-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 0.75rem;
        }
        
        .endpoint {
            font-family: 'JetBrains Mono', monospace;
            background: var(--bg-deep);
            padding: 0.75rem 1rem;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            border: 1px solid var(--border);
        }
        
        .endpoint .method {
            color: var(--accent-warning);
            font-weight: 600;
        }
        
        footer {
            text-align: center;
            margin-top: 4rem;
            padding: 2rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.85rem;
        }
        
        footer a {
            color: var(--accent-primary);
            text-decoration: none;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="brand">
            <div class="brand-icon">XV</div>
            DataVault Enterprise
        </div>
        <span class="status-badge">● SYSTEMS ONLINE</span>
    </nav>
    
    <div class="container">
        <div class="header">
            <h1>XML Processing Gateway</h1>
            <p>Enterprise-grade XML parsing and data transformation services for seamless system integration.</p>
        </div>
        
        <div class="grid">
            <!-- XML Parser -->
            <div class="card">
                <div class="card-header">
                    <h3><span class="card-icon">📄</span> XML Document Parser</h3>
                    <span class="tag warning">DTD Enabled</span>
                </div>
                <p>Parse and validate XML documents. Supports external entity resolution for legacy system compatibility.</p>
                <form method="POST" action="/parse">
                    <textarea name="xml_data" placeholder='<?xml version="1.0"?>
<document>
    <title>Your Title</title>
    <content>Your Content</content>
</document>'></textarea>
                    <button type="submit">Parse Document</button>
                </form>
            </div>
            
            <!-- User Registration -->
            <div class="card">
                <div class="card-header">
                    <h3><span class="card-icon">👤</span> XML User Registration</h3>
                    <span class="tag">API v2</span>
                </div>
                <p>Register new users via XML payload. Integrates with enterprise identity management systems.</p>
                <form method="POST" action="/register">
                    <textarea name="user_xml" placeholder='<?xml version="1.0"?>
<user>
    <username>newuser</username>
    <email>user@example.com</email>
    <role>viewer</role>
</user>'></textarea>
                    <button type="submit">Register User</button>
                </form>
            </div>
            
            <!-- Product Import -->
            <div class="card">
                <div class="card-header">
                    <h3><span class="card-icon">📦</span> Product Data Import</h3>
                    <span class="tag">Batch Mode</span>
                </div>
                <p>Bulk import product catalogs from XML feeds. Supports external DTD references for schema validation.</p>
                <form method="POST" action="/import">
                    <textarea name="product_xml" placeholder='<?xml version="1.0"?>
<products>
    <product id="001">
        <name>Widget Pro</name>
        <price>29.99</price>
    </product>
</products>'></textarea>
                    <button type="submit">Import Products</button>
                </form>
            </div>
            
            <!-- Config Validator -->
            <div class="card">
                <div class="card-header">
                    <h3><span class="card-icon">⚙️</span> Config Validator</h3>
                    <span class="tag warning">Admin</span>
                </div>
                <p>Validate XML configuration files against internal schemas. Entity expansion enabled for config references.</p>
                <form method="POST" action="/validate">
                    <textarea name="config_xml" placeholder='<?xml version="1.0"?>
<config>
    <server>
        <host>localhost</host>
        <port>8080</port>
    </server>
</config>'></textarea>
                    <button type="submit">Validate Config</button>
                </form>
            </div>
            
            <!-- SOAP Request -->
            <div class="card">
                <div class="card-header">
                    <h3><span class="card-icon">🔗</span> SOAP Request Handler</h3>
                    <span class="tag">Legacy</span>
                </div>
                <p>Process SOAP/XML-RPC requests for backward compatibility with legacy enterprise systems.</p>
                <form method="POST" action="/soap">
                    <textarea name="soap_xml" placeholder='<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <GetData>
            <param>value</param>
        </GetData>
    </soap:Body>
</soap:Envelope>'></textarea>
                    <button type="submit">Send Request</button>
                </form>
            </div>
            
            <!-- XPath Query -->
            <div class="card">
                <div class="card-header">
                    <h3><span class="card-icon">🔍</span> XPath Query Engine</h3>
                    <span class="tag">Search</span>
                </div>
                <p>Execute XPath queries against XML documents for advanced data extraction and analysis.</p>
                <form method="POST" action="/xpath">
                    <input type="text" name="xpath_query" placeholder="//user/name">
                    <textarea name="xml_data" placeholder='<?xml version="1.0"?>
<users>
    <user><name>Alice</name></user>
</users>'></textarea>
                    <button type="submit">Execute Query</button>
                </form>
            </div>
        </div>
        
        <div class="info-panel">
            <h4>Available API Endpoints</h4>
            <div class="endpoint-list">
                <div class="endpoint"><span class="method">POST</span> /parse - Parse XML documents</div>
                <div class="endpoint"><span class="method">POST</span> /register - User registration</div>
                <div class="endpoint"><span class="method">POST</span> /import - Product import</div>
                <div class="endpoint"><span class="method">POST</span> /validate - Config validation</div>
                <div class="endpoint"><span class="method">POST</span> /soap - SOAP handler</div>
                <div class="endpoint"><span class="method">POST</span> /xpath - XPath queries</div>
                <div class="endpoint"><span class="method">POST</span> /api/xml - JSON API</div>
            </div>
        </div>
    </div>
    
    <footer>
        &copy; 2026 Omar Santos. All rights reserved.<br>
        <a href="https://websploit.org">WebSploit Labs</a> - Cybersecurity Education
    </footer>
</body>
</html>
"""

# Result Template
RESULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Result - DataVault XML Gateway</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-deep: #0a0e17;
            --bg-surface: #111827;
            --bg-elevated: #1f2937;
            --accent-primary: #10b981;
            --accent-secondary: #06d6a0;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --border: #374151;
            --glow: rgba(16, 185, 129, 0.3);
        }}
        
        body {{
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-deep);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            background-image: 
                radial-gradient(ellipse at top, rgba(16, 185, 129, 0.08) 0%, transparent 50%);
        }}
        
        .container {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 2.5rem;
            max-width: 900px;
            width: 100%;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }}
        
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        
        h2 {{
            font-size: 1.5rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .status {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            padding: 4px 10px;
            border-radius: 4px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-primary);
        }}
        
        .output {{
            font-family: 'JetBrains Mono', monospace;
            background: var(--bg-deep);
            color: var(--accent-secondary);
            padding: 1.5rem;
            border-radius: 8px;
            font-size: 0.85rem;
            white-space: pre-wrap;
            overflow-x: auto;
            border: 1px solid var(--border);
            margin: 1.5rem 0;
            line-height: 1.6;
        }}
        
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: var(--bg-deep);
            padding: 0.875rem 1.5rem;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px var(--glow);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>{icon} {title}</h2>
            <span class="status">PROCESSED</span>
        </div>
        <div class="output">{content}</div>
        <a href="/" class="btn">← Return to Gateway</a>
    </div>
</body>
</html>
"""


def parse_xml_vulnerable(xml_string):
    """
    VULNERABLE: Parse XML with external entity processing enabled.
    This allows XXE attacks by resolving external entities.
    """
    try:
        # VULNERABILITY: lxml with resolve_entities=True allows XXE
        parser = etree.XMLParser(
            resolve_entities=True,
            load_dtd=True,
            no_network=False,  # Allows network access for external entities
            dtd_validation=False
        )
        doc = etree.fromstring(xml_string.encode(), parser)
        return etree.tostring(doc, pretty_print=True, encoding='unicode')
    except etree.XMLSyntaxError as e:
        return f"XML Parsing Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


def extract_text_content(xml_string):
    """Extract all text content from XML for display"""
    try:
        parser = etree.XMLParser(
            resolve_entities=True,
            load_dtd=True,
            no_network=False,
            dtd_validation=False
        )
        doc = etree.fromstring(xml_string.encode(), parser)
        
        result = []
        for elem in doc.iter():
            if elem.text and elem.text.strip():
                result.append(f"{elem.tag}: {elem.text.strip()}")
        
        return "\n".join(result) if result else "No text content found"
    except Exception as e:
        return f"Error extracting content: {str(e)}"


@app.route('/')
def index():
    return HTML_TEMPLATE


@app.route('/parse', methods=['POST'])
def parse_document():
    """Vulnerable endpoint #1: Basic XML parsing with XXE"""
    xml_data = request.form.get('xml_data', '')
    
    if not xml_data.strip():
        return render_template_string(RESULT_TEMPLATE.format(
            icon="⚠️",
            title="Input Required",
            content="Please provide XML data to parse."
        ))
    
    result = f"Input XML:\n{'-' * 50}\n{xml_data}\n\n"
    result += f"Parsed Output:\n{'-' * 50}\n"
    result += parse_xml_vulnerable(xml_data)
    
    return render_template_string(RESULT_TEMPLATE.format(
        icon="📄",
        title="Document Parsed",
        content=result
    ))


@app.route('/register', methods=['POST'])
def register_user():
    """Vulnerable endpoint #2: User registration via XML"""
    user_xml = request.form.get('user_xml', '')
    
    if not user_xml.strip():
        return render_template_string(RESULT_TEMPLATE.format(
            icon="⚠️",
            title="Input Required",
            content="Please provide user XML data."
        ))
    
    try:
        parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)
        doc = etree.fromstring(user_xml.encode(), parser)
        
        # Extract user data (this would normally be saved to database)
        username = doc.findtext('.//username', 'N/A')
        email = doc.findtext('.//email', 'N/A')
        role = doc.findtext('.//role', 'N/A')
        
        result = f"User Registration Processed\n{'=' * 50}\n\n"
        result += f"Username: {username}\n"
        result += f"Email: {email}\n"
        result += f"Role: {role}\n\n"
        result += f"Status: Registration request received.\n"
        result += f"Reference ID: USR-{hash(username) % 100000:05d}"
        
        return render_template_string(RESULT_TEMPLATE.format(
            icon="👤",
            title="Registration Result",
            content=result
        ))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(
            icon="❌",
            title="Registration Failed",
            content=f"Error processing registration:\n{str(e)}"
        ))


@app.route('/import', methods=['POST'])
def import_products():
    """Vulnerable endpoint #3: Product import via XML"""
    product_xml = request.form.get('product_xml', '')
    
    if not product_xml.strip():
        return render_template_string(RESULT_TEMPLATE.format(
            icon="⚠️",
            title="Input Required",
            content="Please provide product XML data."
        ))
    
    try:
        parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)
        doc = etree.fromstring(product_xml.encode(), parser)
        
        products = doc.findall('.//product')
        
        result = f"Product Import Results\n{'=' * 50}\n\n"
        result += f"Products found: {len(products)}\n\n"
        
        for i, product in enumerate(products, 1):
            name = product.findtext('name', 'Unknown')
            price = product.findtext('price', '0.00')
            product_id = product.get('id', f'AUTO-{i}')
            result += f"[{product_id}] {name} - ${price}\n"
        
        if not products:
            result += "Raw content:\n" + extract_text_content(product_xml)
        
        result += f"\nImport Status: Queued for processing"
        
        return render_template_string(RESULT_TEMPLATE.format(
            icon="📦",
            title="Import Complete",
            content=result
        ))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(
            icon="❌",
            title="Import Failed",
            content=f"Error during import:\n{str(e)}"
        ))


@app.route('/validate', methods=['POST'])
def validate_config():
    """Vulnerable endpoint #4: Configuration validation"""
    config_xml = request.form.get('config_xml', '')
    
    if not config_xml.strip():
        return render_template_string(RESULT_TEMPLATE.format(
            icon="⚠️",
            title="Input Required",
            content="Please provide configuration XML."
        ))
    
    try:
        parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)
        doc = etree.fromstring(config_xml.encode(), parser)
        
        result = f"Configuration Validation Report\n{'=' * 50}\n\n"
        result += "✓ XML Well-Formed: Yes\n"
        result += f"✓ Root Element: <{doc.tag}>\n"
        result += f"✓ Child Elements: {len(doc)}\n\n"
        
        result += "Configuration Values:\n" + "-" * 30 + "\n"
        for elem in doc.iter():
            if elem.text and elem.text.strip():
                result += f"  {elem.tag}: {elem.text.strip()}\n"
        
        result += "\nValidation Status: PASSED"
        
        return render_template_string(RESULT_TEMPLATE.format(
            icon="⚙️",
            title="Validation Result",
            content=result
        ))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(
            icon="❌",
            title="Validation Failed",
            content=f"Configuration error:\n{str(e)}"
        ))


@app.route('/soap', methods=['POST'])
def soap_handler():
    """Vulnerable endpoint #5: SOAP request handler"""
    soap_xml = request.form.get('soap_xml', '')
    
    if not soap_xml.strip():
        return render_template_string(RESULT_TEMPLATE.format(
            icon="⚠️",
            title="Input Required",
            content="Please provide SOAP XML request."
        ))
    
    try:
        parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)
        doc = etree.fromstring(soap_xml.encode(), parser)
        
        result = f"SOAP Request Processing\n{'=' * 50}\n\n"
        result += "Request Analysis:\n" + "-" * 30 + "\n"
        
        # Extract SOAP body content
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'soap12': 'http://www.w3.org/2003/05/soap-envelope'
        }
        
        body = doc.find('.//soap:Body', namespaces) or doc.find('.//soap12:Body', namespaces)
        
        if body is not None:
            result += f"SOAP Body found\n"
            for child in body:
                result += f"  Operation: {child.tag}\n"
                for param in child:
                    text = param.text.strip() if param.text else 'N/A'
                    result += f"    {param.tag}: {text}\n"
        else:
            result += "SOAP Body not found. Raw content:\n"
            result += etree.tostring(doc, pretty_print=True, encoding='unicode')
        
        result += "\nSOAP Response Status: Acknowledged"
        
        return render_template_string(RESULT_TEMPLATE.format(
            icon="🔗",
            title="SOAP Response",
            content=result
        ))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(
            icon="❌",
            title="SOAP Error",
            content=f"SOAP processing error:\n{str(e)}"
        ))


@app.route('/xpath', methods=['POST'])
def xpath_query():
    """Vulnerable endpoint #6: XPath query execution"""
    xml_data = request.form.get('xml_data', '')
    xpath_expr = request.form.get('xpath_query', '')
    
    if not xml_data.strip() or not xpath_expr.strip():
        return render_template_string(RESULT_TEMPLATE.format(
            icon="⚠️",
            title="Input Required",
            content="Please provide both XML data and XPath query."
        ))
    
    try:
        parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)
        doc = etree.fromstring(xml_data.encode(), parser)
        
        # Execute XPath query
        results = doc.xpath(xpath_expr)
        
        result = f"XPath Query Results\n{'=' * 50}\n\n"
        result += f"Query: {xpath_expr}\n\n"
        result += f"Results ({len(results)} matches):\n" + "-" * 30 + "\n"
        
        for i, item in enumerate(results, 1):
            if isinstance(item, etree._Element):
                text = item.text.strip() if item.text else etree.tostring(item, encoding='unicode')
                result += f"[{i}] <{item.tag}>: {text}\n"
            else:
                result += f"[{i}] {item}\n"
        
        if not results:
            result += "No matches found."
        
        return render_template_string(RESULT_TEMPLATE.format(
            icon="🔍",
            title="Query Results",
            content=result
        ))
    except Exception as e:
        return render_template_string(RESULT_TEMPLATE.format(
            icon="❌",
            title="Query Failed",
            content=f"XPath error:\n{str(e)}"
        ))


@app.route('/api/xml', methods=['POST'])
def api_xml():
    """Vulnerable API endpoint for XML processing"""
    content_type = request.content_type or ''
    
    if 'xml' in content_type.lower():
        xml_data = request.data.decode('utf-8')
    else:
        xml_data = request.form.get('xml', '') or request.json.get('xml', '') if request.is_json else ''
    
    if not xml_data:
        return jsonify({'error': 'No XML data provided'}), 400
    
    try:
        parser = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=False)
        doc = etree.fromstring(xml_data.encode(), parser)
        
        # Convert XML to dict-like structure
        def elem_to_dict(elem):
            result = {}
            if elem.text and elem.text.strip():
                result['_text'] = elem.text.strip()
            for child in elem:
                child_data = elem_to_dict(child)
                if child.tag in result:
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
            return result if result else (elem.text.strip() if elem.text else None)
        
        return jsonify({
            'status': 'success',
            'root': doc.tag,
            'data': elem_to_dict(doc)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'DataVault XML Gateway',
        'version': '2.4.1'
    })


if __name__ == '__main__':
    create_internal_files()
    app.run(host='0.0.0.0', port=5014, debug=True)

