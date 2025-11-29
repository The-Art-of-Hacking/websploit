from flask import Flask, request, render_template_string, send_file
import os

app = Flask(__name__)

# Setup a directory for "public" files
FILES_DIR = 'files'
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)
    with open(os.path.join(FILES_DIR, 'hello.txt'), 'w') as f:
        f.write("Hello! This is a public file.")
    with open(os.path.join(FILES_DIR, 'notes.txt'), 'w') as f:
        f.write("These are just some public notes.")

@app.route('/', methods=['GET'])
def index():
    filename = request.args.get('file')
    file_content = None
    error = None
    
    if filename:
        # VULNERABILITY: Direct file access without validation/sanitization
        # The application joins the base directory with the user input.
        # If the user inputs "../../../etc/passwd", it will traverse up.
        try:
            # Construct the path
            file_path = os.path.join(FILES_DIR, filename)
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    file_content = f.read()
            else:
                error = "File not found"
        except Exception as e:
            error = str(e)

    # Get list of "allowed" files for display
    files = os.listdir(FILES_DIR)

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Viewer (Path Traversal)</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { border: 1px solid #ccc; padding: 20px; border-radius: 5px; }
            .file-list { background: #f9f9f9; padding: 15px; border-radius: 3px; }
            .file-content { background: #2d2d2d; color: #0f0; padding: 15px; border-radius: 3px; overflow-x: auto; white-space: pre-wrap; margin-top: 20px; }
            .error { color: red; margin-top: 10px; }
            ul { list-style-type: none; padding: 0; }
            li { margin: 5px 0; }
            a { text-decoration: none; color: #007bff; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Document Viewer</h1>
            <p>Select a file to view its contents:</p>
            
            <div class="file-list">
                <ul>
                    {% for f in files %}
                        <li><a href="?file={{ f }}">{{ f }}</a></li>
                    {% endfor %}
                </ul>
            </div>

            {% if error %}
                <div class="error">
                    <strong>Error:</strong> {{ error }}
                </div>
            {% endif %}

            {% if file_content %}
                <h3>Content of "{{ filename }}":</h3>
                <pre class="file-content">{{ file_content }}</pre>
            {% endif %}
        </div>
        
        <div style="margin-top: 50px; font-size: 0.8em; color: #666;">
            <p><strong>Lab Info:</strong> This application is vulnerable to Path Traversal (Directory Traversal).</p>
            <p>The application reads files from the <code>files/</code> directory.</p>
            <p>Try to access files outside this directory using <code>../</code> sequences.</p>
            <p>Example: <code>?file=../../../../etc/passwd</code></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, files=files, filename=filename, file_content=file_content, error=error)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)

