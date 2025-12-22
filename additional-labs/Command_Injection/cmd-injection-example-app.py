# This is a simple command injection example app.
# Instructor: Omar Santos (@santosomar)

from flask import Flask, request, render_template_string
import subprocess

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    output = ''
    error = ''
    target = ''
    
    if request.method == 'POST':
        target = request.form.get('target', '')
        if target:
            command = f"ping -c 3 {target}"
            
            try:
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
        <title>NetOps | Connectivity Check</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #0f172a;
                --secondary: #1e293b;
                --accent: #3b82f6;
                --text: #e2e8f0;
                --text-muted: #94a3b8;
                --border: #334155;
            }
            body {
                background-color: var(--primary);
                color: var(--text);
                font-family: 'Inter', sans-serif;
                margin: 0;
                display: flex;
                justify-content: center;
                min-height: 100vh;
                padding-top: 80px;
            }
            .container {
                width: 100%;
                max-width: 700px;
                padding: 2rem;
            }
            .card {
                background: var(--secondary);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 2rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }
            h1 {
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                color: white;
            }
            p.subtitle {
                color: var(--text-muted);
                margin-bottom: 2rem;
                font-size: 0.95rem;
            }
            .input-group {
                display: flex;
                gap: 0.75rem;
                margin-bottom: 1.5rem;
            }
            input {
                flex: 1;
                background: #0f172a;
                border: 1px solid var(--border);
                padding: 0.75rem 1rem;
                border-radius: 6px;
                color: white;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9rem;
            }
            input:focus {
                outline: none;
                border-color: var(--accent);
                ring: 1px solid var(--accent);
            }
            button {
                background: var(--accent);
                color: white;
                border: none;
                padding: 0 1.5rem;
                border-radius: 6px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.2s;
            }
            button:hover {
                background: #2563eb;
            }
            .terminal {
                background: #000;
                border-radius: 6px;
                padding: 1rem;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                margin-top: 1.5rem;
                border: 1px solid var(--border);
                white-space: pre-wrap;
            }
            .stdout { color: #4ade80; }
            .stderr { color: #f87171; }
            footer {
                margin-top: 2rem;
                text-align: center;
                color: var(--text-muted);
                font-size: 0.8rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>WebSploit Labs NetOps Connectivity Dashboard</h1>
                <p class="subtitle">Internal network diagnostic utility for authorized personnel only.</p>
                
                <form method="POST">
                    <div class="input-group">
                        <input type="text" name="target" placeholder="Enter Hostname or IP" value="{{ target }}" required autocomplete="off">
                        <button type="submit">Ping Host</button>
                    </div>
                </form>

                {% if output %}
                <div class="terminal stdout">{{ output }}</div>
                {% endif %}
                
                {% if error %}
                <div class="terminal stderr">{{ error }}</div>
                {% endif %}
            </div>
            <footer>
                Websploit Labs by Omar Santos. <br>
                Authorized access only. Activity is logged.
            </footer>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, output=output, error=error, target=target)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
