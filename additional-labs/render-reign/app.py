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

from flask import Flask, request, render_template_string

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>WebSploit Labs Template Preview Service</title></head>
<body>
    <h1>WebSploit Labs Template Preview Service</h1>
    <p>Enter your name to generate a custom badge:</p>
    <form>
        <input type="text" name="name" placeholder="Enter name">
        <button type="submit">Preview</button>
    </form>
    <hr>
    <h3>Preview:</h3>
    <p>Hello, %s!</p>
</body>
</html>
"""

@app.route('/')
def home():
    name = request.args.get('name', 'Guest')
    # Vulnerable implementation
    return render_template_string(TEMPLATE % name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5021)

