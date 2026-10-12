# WebSploit Labs - cybersecurity training environment.
# Copyright (C) 2019-2026 Omar Santos <https://websploit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Additional terms under GNU GPL version 3 section 7 are in the COPYRIGHT
# file at the root of this repository.

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

