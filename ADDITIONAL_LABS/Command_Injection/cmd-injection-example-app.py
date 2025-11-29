# cmd-injection-example-app.py
## Created for educational purposes by Omar Santos

# Importing the necessary modules
from flask import Flask, request, render_template_string
import subprocess

# Creating the Flask app
app = Flask(__name__)

# Defining the route for the home page
@app.route('/', methods=['GET', 'POST'])
def index():
    output = ''
    error = ''
    target = ''
    
    if request.method == 'POST':
        target = request.form.get('target', '')
        if target:
            # VULNERABILITY: The input is passed directly to a shell command.
            # Using shell=True allows command chaining with ; | && etc.
            command = f"ping -c 3 {target}"
            
            try:
                # capture_output=True captures stdout and stderr
                # text=True returns string instead of bytes
                # shell=True is the key vulnerability here
                proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                
                if proc.returncode == 0:
                    output = proc.stdout
                else:
                    error = proc.stderr or proc.stdout or "Command failed"
                    
            except subprocess.TimeoutExpired:
                error = "Command timed out"
            except Exception as e:
                error = str(e)

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Network Diagnostics Tool</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-color: #0f172a;
                --card-bg: #1e293b;
                --text-primary: #f8fafc;
                --text-secondary: #94a3b8;
                --accent: #3b82f6;
                --accent-hover: #2563eb;
                --error: #ef4444;
                --success: #22c55e;
                --terminal-bg: #000000;
            }
            
            * { box-sizing: border-box; margin: 0; padding: 0; }
            
            body {
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-primary);
                line-height: 1.5;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 40px 20px;
            }
            
            .main-container {
                width: 100%;
                max-width: 800px;
                background: var(--card-bg);
                border-radius: 12px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                padding: 40px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            h1 {
                font-size: 1.875rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                background: linear-gradient(to right, #60a5fa, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            
            .subtitle {
                color: var(--text-secondary);
                margin-bottom: 2rem;
            }
            
            .input-group {
                display: flex;
                gap: 10px;
                margin-bottom: 2rem;
            }
            
            input[type="text"] {
                flex: 1;
                background: rgba(15, 23, 42, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: var(--text-primary);
                padding: 12px 16px;
                border-radius: 8px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 1rem;
                transition: all 0.2s;
            }
            
            input[type="text"]:focus {
                outline: none;
                border-color: var(--accent);
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
            }
            
            button {
                background: var(--accent);
                color: white;
                border: none;
                padding: 0 24px;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            
            button:hover {
                background: var(--accent-hover);
            }
            
            .terminal-window {
                background: var(--terminal-bg);
                border-radius: 8px;
                overflow: hidden;
                margin-top: 2rem;
                border: 1px solid #333;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            }
            
            .terminal-header {
                background: #1a1a1a;
                padding: 8px 16px;
                display: flex;
                align-items: center;
                gap: 6px;
                border-bottom: 1px solid #333;
            }
            
            .dot { width: 12px; height: 12px; border-radius: 50%; }
            .dot.red { background: #ff5f56; }
            .dot.yellow { background: #ffbd2e; }
            .dot.green { background: #27c93f; }
            
            .terminal-content {
                padding: 16px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9rem;
                overflow-x: auto;
                white-space: pre-wrap;
            }
            
            .output-success { color: #4ade80; }
            .output-error { color: #f87171; }
            
            .info-box {
                margin-top: 3rem;
                padding: 16px;
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 8px;
                font-size: 0.9rem;
                color: var(--text-secondary);
            }
            
            code {
                background: rgba(0, 0, 0, 0.3);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'JetBrains Mono', monospace;
                color: var(--accent);
            }
        </style>
    </head>
    <body>
        <div class="main-container">
            <h1>Network Diagnostics</h1>
            <p class="subtitle">Secure Enterprise Ping Utility</p>
            
            <form method="POST">
                <div class="input-group">
                    <input type="text" name="target" placeholder="Enter IP address (e.g., 8.8.8.8)" value="{{ target }}" autocomplete="off">
                    <button type="submit">
                        Execute Ping
                    </button>
                </div>
            </form>
            
            {% if error %}
                <div class="terminal-window">
                    <div class="terminal-header">
                        <div class="dot red"></div>
                        <div class="dot yellow"></div>
                        <div class="dot green"></div>
                        <span style="margin-left: 10px; font-size: 12px; color: #666;">stderr</span>
                    </div>
                    <pre class="terminal-content output-error">{{ error }}</pre>
                </div>
            {% endif %}

            {% if output %}
                <div class="terminal-window">
                    <div class="terminal-header">
                        <div class="dot red"></div>
                        <div class="dot yellow"></div>
                        <div class="dot green"></div>
                        <span style="margin-left: 10px; font-size: 12px; color: #666;">stdout</span>
                    </div>
                    <pre class="terminal-content output-success">{{ output }}</pre>
                </div>
            {% endif %}
            
            <div class="info-box">
                <p><strong>⚠️ Security Training Lab:</strong> This application contains a Command Injection vulnerability.</p>
                <p style="margin-top: 8px">Payload examples:</p>
                <ul style="margin-left: 20px; margin-top: 4px;">
                    <li><code>127.0.0.1; ls -la</code></li>
                    <li><code>127.0.0.1 && whoami</code></li>
                    <li><code>127.0.0.1 | cat /etc/passwd</code></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, output=output, error=error, target=target)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

