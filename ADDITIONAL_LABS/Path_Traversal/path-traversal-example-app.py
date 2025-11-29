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
        try:
            # Construct the path
            file_path = os.path.join(FILES_DIR, filename)
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    file_content = f.read()
            else:
                error = "Document not found in repository."
        except Exception:
            error = "An error occurred while retrieving the document."

    # Get list of "allowed" files for display
    files = os.listdir(FILES_DIR)

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Corporate Document Repository</title>
        <style>
            :root {
                --primary-color: #0056b3;
                --secondary-color: #f8f9fa;
                --text-color: #333;
                --border-color: #dee2e6;
                --bg-color: #ffffff;
                --sidebar-width: 280px;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f6f8;
                color: var(--text-color);
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            header {
                background-color: var(--primary-color);
                color: white;
                padding: 1rem 2rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: space-between;
                z-index: 10;
            }
            .brand {
                font-size: 1.25rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .user-profile {
                font-size: 0.9rem;
                opacity: 0.9;
            }
            .main-container {
                display: flex;
                flex: 1;
                overflow: hidden;
            }
            .sidebar {
                width: var(--sidebar-width);
                background-color: var(--bg-color);
                border-right: 1px solid var(--border-color);
                overflow-y: auto;
                padding: 1.5rem;
                display: flex;
                flex-direction: column;
            }
            .sidebar-title {
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #6c757d;
                margin-bottom: 1rem;
                font-weight: 700;
            }
            .file-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            .file-list li {
                margin-bottom: 0.5rem;
            }
            .file-link {
                display: block;
                padding: 0.5rem 0.75rem;
                color: var(--text-color);
                text-decoration: none;
                border-radius: 4px;
                transition: background-color 0.2s;
                font-size: 0.95rem;
            }
            .file-link:hover {
                background-color: var(--secondary-color);
                color: var(--primary-color);
            }
            .file-link.active {
                background-color: #e7f1ff;
                color: var(--primary-color);
                font-weight: 500;
            }
            .content-area {
                flex: 1;
                padding: 2rem;
                overflow-y: auto;
                background-color: #f4f6f8;
            }
            .document-card {
                background-color: var(--bg-color);
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                padding: 2rem;
                min-height: 300px;
            }
            .document-header {
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 1rem;
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .document-title {
                font-size: 1.5rem;
                font-weight: 600;
                color: var(--text-color);
                margin: 0;
            }
            .document-meta {
                font-size: 0.85rem;
                color: #6c757d;
            }
            .document-body {
                font-family: "Monaco", "Consolas", "Courier New", monospace;
                font-size: 0.9rem;
                line-height: 1.6;
                white-space: pre-wrap;
                color: #24292e;
                background-color: #f6f8fa;
                padding: 1rem;
                border-radius: 4px;
                border: 1px solid #eaecef;
            }
            .empty-state {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: #6c757d;
                text-align: center;
            }
            .error-message {
                background-color: #fde8e8;
                color: #c53030;
                padding: 1rem;
                border-radius: 4px;
                margin-bottom: 1rem;
                border: 1px solid #fecaca;
            }
            .icon-doc { margin-right: 8px; }
        </style>
    </head>
    <body>
        <header>
            <div class="brand">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                DocuShare Enterprise
            </div>
            <div class="user-profile">
                <span>Logged in as: <strong>Guest User</strong></span>
            </div>
        </header>
        <div class="main-container">
            <aside class="sidebar">
                <div class="sidebar-title">Repository Files</div>
                <ul class="file-list">
                    {% for f in files %}
                        <li>
                            <a href="?file={{ f }}" class="file-link {% if filename == f %}active{% endif %}">
                                <span class="icon-doc">📄</span> {{ f }}
                            </a>
                        </li>
                    {% endfor %}
                </ul>
                
                <div style="margin-top: auto; padding-top: 1rem; border-top: 1px solid var(--border-color); font-size: 0.8rem; color: #999;">
                    &copy; 2026 Omar Santos. All rights reserved. <br>Internal Use Only
                </div>
            </aside>
            <main class="content-area">
                {% if error %}
                    <div class="error-message">
                        <strong>Error:</strong> {{ error }}
                    </div>
                {% endif %}

                <div class="document-card">
                    {% if file_content %}
                        <div class="document-header">
                            <h2 class="document-title">{{ filename }}</h2>
                            <div class="document-meta">Read-only Mode</div>
                        </div>
                        <div class="document-body">{{ file_content }}</div>
                    {% elif not error %}
                        <div class="empty-state">
                            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 1rem; opacity: 0.5;"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>
                            <h3>Select a document to view</h3>
                            <p>Choose a file from the sidebar to preview its contents.</p>
                        </div>
                    {% else %}
                         <div class="empty-state">
                            <p>Unable to display content.</p>
                        </div>
                    {% endif %}
                </div>
            </main>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, files=files, filename=filename, file_content=file_content, error=error)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
