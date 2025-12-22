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

