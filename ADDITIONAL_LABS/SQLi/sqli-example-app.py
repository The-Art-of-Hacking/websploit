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
    query_log = None
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # VULNERABILITY: Constructing SQL query using string formatting
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        query_log = query
        
        try:
            cursor.executescript(query) # executescript allows multiple statements (more dangerous), though fetchall gets the first result set usually
            # For standard login bypass, execute is enough, but let's stick to the classic select
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
    <html>
    <head>
        <title>SQL Injection Example</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { border: 1px solid #ccc; padding: 20px; border-radius: 5px; }
            input[type="text"], input[type="password"] { padding: 8px; width: 300px; margin-bottom: 10px; display: block; }
            button { padding: 8px 15px; background: #28a745; color: white; border: none; border-radius: 3px; cursor: pointer; }
            .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 3px; }
            .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 3px; }
            .debug { background: #f8f9fa; padding: 10px; border: 1px dashed #999; margin-top: 20px; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Login Portal</h1>
            <p>Please enter your credentials to access the secure area.</p>
            
            <form method="POST">
                <label>Username:</label>
                <input type="text" name="username" placeholder="admin">
                <label>Password:</label>
                <input type="password" name="password" placeholder="password">
                <button type="submit">Login</button>
            </form>
            
            {% if error %}
                <div class="error" style="margin-top: 20px;">
                    {{ error }}
                </div>
            {% endif %}

            {% if result %}
                <div class="success" style="margin-top: 20px;">
                    <h3>Success!</h3>
                    <p>{{ result }}</p>
                </div>
            {% endif %}
            
            {% if query_log %}
                <div class="debug">
                    <strong>Debug (Executed Query):</strong><br>
                    {{ query_log }}
                </div>
            {% endif %}
        </div>
        <div style="margin-top: 50px; font-size: 0.8em; color: #666;">
            <p><strong>Lab Info:</strong> This login form is vulnerable to SQL Injection (SQLi).</p>
            <p>Try to bypass authentication using: <code>' OR '1'='1</code></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, result=result, error=error, query_log=query_log)

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(host='0.0.0.0', port=5000)

