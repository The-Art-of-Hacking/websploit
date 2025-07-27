#!/usr/bin/env python3
"""
WebSploit Labs - XSS Vulnerable Application
Created for educational purposes by Omar Santos
This application demonstrates various XSS vulnerabilities
"""

from flask import Flask, request, render_template_string, jsonify, make_response, redirect, url_for, session
import urllib.parse
import html
import json
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'websploit-labs-secret-key-for-education'

# In-memory storage for demo purposes
comments = []
user_profiles = {}
search_history = []
messages = []

# HTML template for the main page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSploit Labs - Social Platform</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .nav { background: #007bff; padding: 15px; margin: -30px -30px 30px -30px; border-radius: 10px 10px 0 0; }
        .nav a { color: white; text-decoration: none; margin-right: 20px; padding: 8px 15px; border-radius: 4px; }
        .nav a:hover { background: rgba(255,255,255,0.2); }
        .section { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff; }
        input[type="text"], textarea { width: 70%; padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        button:hover { background: #0056b3; }
        .result { background: #e9ecef; padding: 15px; margin-top: 10px; border-radius: 4px; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .comment { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #ddd; }
        .comment-meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }
        .profile { background: #e3f2fd; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .search-result { background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #007bff; }
        .message { background: #fff3e0; padding: 10px; margin: 5px 0; border-radius: 4px; }
    </style>
    <script>
        function searchUsers() {
            const query = document.getElementById('searchInput').value;
            fetch('/api/search?q=' + encodeURIComponent(query))
                .then(response => response.json())
                .then(data => {
                    document.getElementById('searchResults').innerHTML = data.html;
                });
        }
        
        function loadProfile(username) {
            window.location.href = '/profile?user=' + username;
        }
        
        function showMessage(msg) {
            alert('Message: ' + msg);
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/">🏠 Home</a>
            <a href="/comments">💬 Comments</a>
            <a href="/profile">👤 Profile</a>
            <a href="/search">🔍 Search</a>
            <a href="/messages">📧 Messages</a>
            <a href="/admin">⚙️ Admin</a>
        </div>
        
        <h1>🌐 WebSploit Labs - Social Platform</h1>
        <div class="warning">
            ⚠️ <strong>Educational Environment:</strong> This application contains intentional XSS vulnerabilities for learning purposes.
        </div>
        
        <div class="section">
            <h3>🎯 Available XSS Testing Areas</h3>
            <p>Explore different XSS vulnerability types:</p>
            <ul>
                <li><strong>Reflected XSS</strong> - Search functionality and URL parameters</li>
                <li><strong>Stored XSS</strong> - Comment system and user profiles</li>
                <li><strong>DOM XSS</strong> - Client-side JavaScript processing</li>
                <li><strong>Context-based XSS</strong> - Different injection contexts</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_TEMPLATE

# Reflected XSS Vulnerabilities
@app.route('/search')
def search_page():
    query = request.args.get('q', '')
    filter_type = request.args.get('type', 'all')
    
    # VULNERABILITY 1: Reflected XSS in search parameter
    search_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Search Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .search-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .result {{ background: white; padding: 15px; margin: 10px 0; border-radius: 4px; border: 1px solid #ddd; }}
            .no-results {{ color: #666; font-style: italic; }}
            input {{ padding: 10px; width: 300px; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <h2>🔍 Search Platform</h2>
        <div class="search-box">
            <form method="GET">
                <input type="text" name="q" value="{query}" placeholder="Search users, posts, comments...">
                <select name="type">
                    <option value="all" {'selected' if filter_type == 'all' else ''}>All</option>
                    <option value="users" {'selected' if filter_type == 'users' else ''}>Users</option>
                    <option value="posts" {'selected' if filter_type == 'posts' else ''}>Posts</option>
                </select>
                <button type="submit">Search</button>
            </form>
        </div>
        
        <div class="results">
            <h3>Search Results for: {query}</h3>
    """
    
    if query:
        # Simulate search results with XSS vulnerability
        search_html += f"""
            <div class="result">
                <h4>User Profile: {query}</h4>
                <p>Showing results for search term: <strong>{query}</strong></p>
                <p>Filter applied: {filter_type}</p>
            </div>
            <div class="result">
                <h4>Recent Post</h4>
                <p>Found post containing "{query}" by user123</p>
            </div>
        """
        
        # Store search history (another XSS vector)
        search_history.append({
            'query': query,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'filter': filter_type
        })
    else:
        search_html += '<div class="no-results">Enter a search term to find content...</div>'
    
    search_html += """
        </div>
        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    """
    
    return search_html

@app.route('/profile')
def profile_page():
    username = request.args.get('user', 'guest')
    bio = request.args.get('bio', '')
    
    # VULNERABILITY 2: Reflected XSS in profile parameters
    profile_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Profile - {username}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .profile-header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
            .profile-info {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .edit-form {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px; }}
            input, textarea {{ width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
        </style>
        <script>
            function updateProfile() {{
                const newBio = document.getElementById('bioInput').value;
                window.location.href = '/profile?user={username}&bio=' + encodeURIComponent(newBio);
            }}
        </script>
    </head>
    <body>
        <div class="profile-header">
            <h1>👤 {username}'s Profile</h1>
            <p>Welcome to the user profile page</p>
        </div>
        
        <div class="profile-info">
            <h3>Profile Information</h3>
            <p><strong>Username:</strong> {username}</p>
            <p><strong>Bio:</strong> {bio if bio else 'No bio provided'}</p>
            <p><strong>Member Since:</strong> 2024</p>
            <p><strong>Status:</strong> <span style="color: green;">Active</span></p>
        </div>
        
        <div class="edit-form">
            <h3>Update Bio</h3>
            <textarea id="bioInput" placeholder="Tell us about yourself..." rows="4">{bio}</textarea>
            <br>
            <button onclick="updateProfile()">Update Profile</button>
        </div>
        
        <div style="margin-top: 20px;">
            <a href="/">← Back to Home</a> | 
            <a href="/profile?user=admin">View Admin Profile</a>
        </div>
    </body>
    </html>
    """
    
    return profile_html

# Stored XSS Vulnerabilities
@app.route('/comments', methods=['GET', 'POST'])
def comments_page():
    if request.method == 'POST':
        name = request.form.get('name', 'Anonymous')
        comment = request.form.get('comment', '')
        email = request.form.get('email', '')
        
        # VULNERABILITY 3: Stored XSS in comments
        if comment:
            comments.append({
                'id': len(comments) + 1,
                'name': name,
                'email': email,
                'comment': comment,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
    
    comments_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Comments Section</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .comment-form { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
            .comment { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .comment-meta { color: #666; font-size: 0.9em; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
            .comment-text { line-height: 1.6; }
            input, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
            button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; }
            .admin-comment { border-left: 4px solid #dc3545; }
        </style>
    </head>
    <body>
        <h2>💬 Community Comments</h2>
        
        <div class="comment-form">
            <h3>Leave a Comment</h3>
            <form method="POST">
                <input type="text" name="name" placeholder="Your Name" required>
                <input type="email" name="email" placeholder="Your Email (optional)">
                <textarea name="comment" placeholder="Your comment..." rows="4" required></textarea>
                <button type="submit">Post Comment</button>
            </form>
        </div>
        
        <div class="comments-list">
            <h3>Recent Comments (""" + str(len(comments)) + """):</h3>
    """
    
    # Display comments with XSS vulnerability
    for comment in reversed(comments[-10:]):  # Show last 10 comments
        admin_class = ' admin-comment' if 'admin' in comment['name'].lower() else ''
        comments_html += f"""
            <div class="comment{admin_class}">
                <div class="comment-meta">
                    <strong>{comment['name']}</strong> 
                    {f"&lt;{comment['email']}&gt;" if comment['email'] else ""} 
                    - {comment['timestamp']}
                </div>
                <div class="comment-text">{comment['comment']}</div>
            </div>
        """
    
    if not comments:
        comments_html += '<p style="color: #666; font-style: italic;">No comments yet. Be the first to comment!</p>'
    
    comments_html += """
        </div>
        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    """
    
    return comments_html

# DOM XSS Vulnerabilities
@app.route('/messages')
def messages_page():
    # VULNERABILITY 4: DOM XSS through URL fragment processing
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Message Center</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .message-center { max-width: 800px; margin: 0 auto; }
            .message-input { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .message { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #007bff; }
            .urgent { border-left-color: #dc3545 !important; background: #fff5f5; }
            input { padding: 10px; width: 300px; border: 1px solid #ddd; border-radius: 4px; margin: 5px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
            .preview { background: #e9ecef; padding: 15px; margin: 10px 0; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="message-center">
            <h2>📧 Message Center</h2>
            
            <div class="message-input">
                <h3>Send a Message</h3>
                <input type="text" id="recipientInput" placeholder="Recipient">
                <input type="text" id="subjectInput" placeholder="Subject">
                <br>
                <textarea id="messageInput" placeholder="Your message..." rows="4" style="width: 100%; padding: 10px; margin: 5px 0;"></textarea>
                <br>
                <button onclick="sendMessage()">Send Message</button>
                <button onclick="previewMessage()">Preview</button>
            </div>
            
            <div id="preview" class="preview" style="display: none;">
                <h4>Message Preview:</h4>
                <div id="previewContent"></div>
            </div>
            
            <div class="messages-list">
                <h3>Recent Messages:</h3>
                <div id="messagesList">
                    <div class="message">
                        <strong>System</strong> - Welcome to WebSploit Labs!<br>
                        <small>This is a test message to demonstrate the message system.</small>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // DOM XSS vulnerability in message processing
            function previewMessage() {
                const recipient = document.getElementById('recipientInput').value;
                const subject = document.getElementById('subjectInput').value;
                const message = document.getElementById('messageInput').value;
                
                const previewDiv = document.getElementById('preview');
                const previewContent = document.getElementById('previewContent');
                
                // VULNERABLE: Direct innerHTML assignment without sanitization
                previewContent.innerHTML = `
                    <strong>To:</strong> ${recipient}<br>
                    <strong>Subject:</strong> ${subject}<br>
                    <strong>Message:</strong><br>
                    <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0;">${message}</div>
                `;
                
                previewDiv.style.display = 'block';
            }
            
            function sendMessage() {
                const recipient = document.getElementById('recipientInput').value;
                const subject = document.getElementById('subjectInput').value;
                const message = document.getElementById('messageInput').value;
                
                if (!recipient || !message) {
                    alert('Please fill in recipient and message fields');
                    return;
                }
                
                // VULNERABLE: Direct innerHTML assignment
                const messagesList = document.getElementById('messagesList');
                const newMessage = document.createElement('div');
                newMessage.className = 'message';
                newMessage.innerHTML = `
                    <strong>To: ${recipient}</strong> - ${subject}<br>
                    <small>${message}</small>
                `;
                
                messagesList.appendChild(newMessage);
                
                // Clear form
                document.getElementById('recipientInput').value = '';
                document.getElementById('subjectInput').value = '';
                document.getElementById('messageInput').value = '';
                document.getElementById('preview').style.display = 'none';
                
                alert('Message sent to ' + recipient);
            }
            
            // Process URL fragment for auto-fill (DOM XSS vector)
            window.onload = function() {
                const hash = window.location.hash.substring(1);
                if (hash) {
                    const params = new URLSearchParams(hash);
                    const autoFillMsg = params.get('msg');
                    const autoFillRecipient = params.get('to');
                    
                    if (autoFillMsg) {
                        // VULNERABLE: Direct assignment from URL
                        document.getElementById('messageInput').value = decodeURIComponent(autoFillMsg);
                    }
                    if (autoFillRecipient) {
                        document.getElementById('recipientInput').value = decodeURIComponent(autoFillRecipient);
                    }
                }
            };
        </script>
        
        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    """

# API endpoints with XSS vulnerabilities
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    
    # VULNERABILITY 5: XSS in JSON API response
    results_html = f"""
        <div class="search-results">
            <h4>Search Results for: {query}</h4>
    """
    
    if query:
        # Simulate search results
        fake_results = [
            f"User profile containing '{query}'",
            f"Blog post about {query}",
            f"Comment mentioning {query}"
        ]
        
        for result in fake_results:
            results_html += f'<div class="search-result">{result}</div>'
    else:
        results_html += '<div class="no-results">No search query provided</div>'
    
    results_html += '</div>'
    
    return jsonify({
        'query': query,
        'count': 3 if query else 0,
        'html': results_html  # XSS vulnerability: HTML in JSON response
    })

@app.route('/api/profile/<username>')
def api_profile(username):
    bio = request.args.get('bio', f'This is {username}\'s profile')
    
    # VULNERABILITY 6: XSS in API responses
    return jsonify({
        'username': username,
        'bio': bio,  # Not sanitized
        'html_bio': f'<div class="bio">{bio}</div>',  # Direct HTML inclusion
        'status': 'active'
    })

# Admin panel (typically higher privilege target)
@app.route('/admin')
def admin_panel():
    session_id = request.args.get('session', '')
    debug_info = request.args.get('debug', '')
    
    # VULNERABILITY 7: XSS in admin panel
    admin_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Panel</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }}
            .admin-header {{ background: #dc3545; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .admin-section {{ background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .debug-info {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; font-family: monospace; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f8f9fa; }}
        </style>
    </head>
    <body>
        <div class="admin-header">
            <h1>⚙️ Admin Control Panel</h1>
            <p>System Administration Interface</p>
            {f'<p>Session: {session_id}</p>' if session_id else ''}
        </div>
        
        <div class="admin-section">
            <h3>📊 System Statistics</h3>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Comments</td><td>{len(comments)}</td></tr>
                <tr><td>Search Queries</td><td>{len(search_history)}</td></tr>
                <tr><td>Active Sessions</td><td>1</td></tr>
            </table>
        </div>
        
        <div class="admin-section">
            <h3>💬 Recent Comments</h3>
    """
    
    # Display recent comments (with XSS vulnerability)
    for comment in comments[-5:]:
        admin_html += f"""
            <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0;">
                <strong>{comment['name']}</strong>: {comment['comment']}
                <br><small>{comment['timestamp']}</small>
            </div>
        """
    
    admin_html += """
        </div>
        
        <div class="admin-section">
            <h3>🔍 Search History</h3>
    """
    
    # Display search history (with XSS vulnerability)
    for search in search_history[-5:]:
        admin_html += f"""
            <div style="border: 1px solid #ddd; padding: 8px; margin: 3px 0;">
                Query: <strong>{search['query']}</strong> | 
                Filter: {search['filter']} | 
                Time: {search['timestamp']}
            </div>
        """
    
    if debug_info:
        admin_html += f"""
            <div class="admin-section">
                <h3>🐛 Debug Information</h3>
                <div class="debug-info">
                    Debug Data: {debug_info}
                </div>
            </div>
        """
    
    admin_html += """
        </div>
        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    """
    
    return admin_html

# Context-based XSS vulnerabilities
@app.route('/widget')
def widget():
    title = request.args.get('title', 'Default Widget')
    callback = request.args.get('callback', '')
    config = request.args.get('config', '{}')
    
    # VULNERABILITY 8: XSS in different contexts (JavaScript, HTML attributes, etc.)
    widget_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            .widget {{ border: 2px solid #007bff; padding: 20px; border-radius: 8px; max-width: 400px; margin: 20px auto; }}
        </style>
        <script>
            // XSS in JavaScript context
            var widgetConfig = {config};
            var widgetTitle = "{title}";
            
            function initWidget() {{
                console.log("Initializing widget: " + widgetTitle);
                {f'{callback}();' if callback else ''}
            }}
            
            window.onload = initWidget;
        </script>
    </head>
    <body>
        <div class="widget" title="{title}">
            <h3>🔧 Widget: {title}</h3>
            <p>This is a configurable widget component.</p>
            <p>Configuration: <code>{config}</code></p>
        </div>
    </body>
    </html>
    """
    
    return widget_html

if __name__ == '__main__':
    print("🚀 WebSploit Labs - XSS Vulnerable Application")
    print("⚠️  WARNING: This application contains intentional XSS vulnerabilities!")
    print("📚 Educational use only - Created by Omar Santos")
    print("🌐 Access the application at: http://localhost:5011")
    print("=" * 60)
    print("🎯 XSS Testing Areas:")
    print("   • Reflected XSS: /search, /profile")
    print("   • Stored XSS: /comments")
    print("   • DOM XSS: /messages")
    print("   • Context XSS: /widget, /admin")
    print("   • API XSS: /api/search, /api/profile")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5011, debug=True)