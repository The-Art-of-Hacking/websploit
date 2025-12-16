from flask import Flask, request, render_template_string, g
import sqlite3
import os

app = Flask(__name__)
DATABASE = 'users.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, secret TEXT)")
        cursor.execute("INSERT INTO users (username, password, secret) VALUES ('admin', 'supersecretpass', 'Flag: SQLI_MASTER_ADMIN_ACCESS')")
        cursor.execute("INSERT INTO users (username, password, secret) VALUES ('user', 'user123', 'Just a regular user secret')")
        db.commit()

@app.route('/', methods=['GET', 'POST'])
def login():
    result = None
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # VULNERABILITY: Constructing SQL query using string formatting
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        
        try:
            cursor.executescript(query) # executescript allows multiple statements (more dangerous)
            # Re-running as standard execute for the select part if script didn't return rows directly in this context
            cursor.execute(query)
            user = cursor.fetchone()
            
            if user:
                result = f"Welcome, {user[1]}! Your secret is: {user[3]}"
            else:
                error = "Invalid credentials"
        except Exception as e:
            error = f"Database Error: {str(e)}"

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Secure Corporate Portal</title>
        <style>
            :root {
                --primary: #0f172a;
                --primary-hover: #1e293b;
                --accent: #3b82f6;
                --bg: #f1f5f9;
                --surface: #ffffff;
                --text: #334155;
                --border: #e2e8f0;
                --error: #ef4444;
                --success: #10b981;
            }
            body {
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background-color: var(--bg);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                color: var(--text);
            }
            .login-card {
                background: var(--surface);
                width: 100%;
                max-width: 400px;
                padding: 2.5rem;
                border-radius: 1rem;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
                border: 1px solid var(--border);
            }
            .header {
                text-align: center;
                margin-bottom: 2rem;
            }
            .header h1 {
                color: var(--primary);
                font-size: 1.5rem;
                font-weight: 700;
                margin: 0;
                letter-spacing: -0.025em;
            }
            .header p {
                color: #64748b;
                font-size: 0.875rem;
                margin-top: 0.5rem;
            }
            .form-group {
                margin-bottom: 1.25rem;
            }
            .form-group label {
                display: block;
                font-size: 0.875rem;
                font-weight: 500;
                color: var(--primary);
                margin-bottom: 0.5rem;
            }
            .form-group input {
                width: 100%;
                padding: 0.75rem 1rem;
                border: 1px solid var(--border);
                border-radius: 0.5rem;
                font-size: 0.95rem;
                transition: all 0.2s;
                box-sizing: border-box;
            }
            .form-group input:focus {
                outline: none;
                border-color: var(--accent);
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            }
            button {
                width: 100%;
                background-color: var(--primary);
                color: white;
                padding: 0.75rem;
                border: none;
                border-radius: 0.5rem;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            button:hover {
                background-color: var(--primary-hover);
            }
            .message {
                margin-top: 1.5rem;
                padding: 1rem;
                border-radius: 0.5rem;
                font-size: 0.875rem;
                display: flex;
                align-items: center;
            }
            .error {
                background-color: #fef2f2;
                color: var(--error);
                border: 1px solid #fecaca;
            }
            .success {
                background-color: #ecfdf5;
                color: var(--success);
                border: 1px solid #a7f3d0;
            }
            .footer {
                margin-top: 2rem;
                text-align: center;
                font-size: 0.75rem;
                color: #94a3b8;
            }
        </style>
    </head>
    <body>
        <div class="login-card">
            <div class="header">
                <h1>Employee Portal</h1>
                <p>Please sign in to access internal resources</p>
            </div>
            <form method="POST">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required autocomplete="current-password">
                </div>
                <button type="submit">Sign In</button>
            </form>

            {% if error %}
            <div class="message error">
                {{ error }}
            </div>
            {% endif %}

            {% if result %}
            <div class="message success">
                {{ result }}
            </div>
            {% endif %}

            <div class="footer">
                &copy; 2026 Omar Santos. All rights reserved. <br>Authorized personnel only.
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, result=result, error=error)

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(host='0.0.0.0', port=5000)
