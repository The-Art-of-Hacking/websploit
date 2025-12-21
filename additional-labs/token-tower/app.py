from flask import Flask, request, jsonify, render_template_string
import jwt
import datetime

app = Flask(__name__)
# Weak secret for educational purposes
SECRET_KEY = "secret123"

LOGIN_PAGE = """
<h2>Token Tower Login</h2>
<form method="POST" action="/login">
    <input type="text" name="username" placeholder="Username">
    <input type="password" name="password" placeholder="Password">
    <input type="submit" value="Login">
</form>
"""

DASHBOARD = """
<h2>Welcome to the Tower, {{ user }}!</h2>
<p>Your Role: {{ role }}</p>
{% if role == 'admin' %}
    <p style="color:red;">FLAG: WEBSPLOIT{JWT_M4ST3R_BYP4SS}</p>
{% else %}
    <p>You are a guest. Only admins can see the flag.</p>
{% endif %}
"""

@app.route('/', methods=['GET'])
def home():
    token = request.cookies.get('auth_token')
    if not token:
        return LOGIN_PAGE
    
    try:
        # INTENTIONAL VULNERABILITY 1: Allowing "none" algorithm if header specifies it
        # INTENTIONAL VULNERABILITY 2: Weak secret "secret123"
        header = jwt.get_unverified_header(token)
        if header.get('alg') == 'none':
            data = jwt.decode(token, options={"verify_signature": False})
        else:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            
        return render_template_string(DASHBOARD, user=data['user'], role=data['role'])
    except Exception as e:
        return f"Invalid Token: {str(e)} <br> <a href='/'>Login again</a>"

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    # Default role is guest
    token = jwt.encode({
        'user': username,
        'role': 'guest',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    }, SECRET_KEY, algorithm='HS256')
    
    resp = Flask(__name__).make_response("Logged in! Check your cookies. Refresh to see dashboard.")
    resp.set_cookie('auth_token', token)
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5020)

