from flask import Flask, request, make_response, render_template_string
import pickle
import base64

app = Flask(__name__)

HOME_HTML = """
<h2>WebSploit Labs Deserialization Gateway</h2>
<p>We use advanced Python objects to store your preferences cookie.</p>
<p>Current Preference: {{ pref }}</p>
<form method="POST" action="/set_pref">
    <input type="text" name="pref" placeholder="Dark Mode / Light Mode">
    <button type="submit">Save Preference</button>
</form>
"""

class UserPrefs:
    def __init__(self, mode):
        self.mode = mode
    def __str__(self):
        return self.mode

@app.route('/')
def index():
    cookie_data = request.cookies.get('user_prefs')
    if cookie_data:
        try:
            # VULNERABILITY: Insecure pickle.loads of user controlled data
            pref_obj = pickle.loads(base64.b64decode(cookie_data))
            return render_template_string(HOME_HTML, pref=str(pref_obj))
        except:
            return render_template_string(HOME_HTML, pref="Corrupted Data")
    return render_template_string(HOME_HTML, pref="Default")

@app.route('/set_pref', methods=['POST'])
def set_pref():
    mode = request.form.get('pref', 'Light Mode')
    pref_obj = UserPrefs(mode)
    serialized = base64.b64encode(pickle.dumps(pref_obj)).decode()
    
    resp = make_response("Preference saved!")
    resp.set_cookie('user_prefs', serialized)
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5022)

