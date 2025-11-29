#!/usr/bin/env python3
"""
SecretCorp Application
"""

from flask import Flask, request, render_template_string, jsonify, make_response, redirect, url_for, session
import urllib.parse
import html
import json
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'SecretCorp-secret-key'

# In-memory storage
comments = []
user_profiles = {}
search_history = []
messages = []

# HTML template for the main page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecretCorp</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --bg: #f9fafb;
            --card: #ffffff;
            --text: #1f2937;
            --text-light: #6b7280;
            --border: #e5e7eb;
        }
        body { font-family: 'Inter', sans-serif; margin: 0; background: var(--bg); color: var(--text); line-height: 1.5; }
        .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
        .nav { background: white; padding: 0 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 10; }
        .nav-content { max-width: 1100px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 64px; }
        .nav-logo { font-weight: 700; font-size: 1.25rem; color: var(--primary); text-decoration: none; display: flex; align-items: center; gap: 8px; }
        .nav-links { display: flex; gap: 20px; }
        .nav-links a { color: var(--text-light); text-decoration: none; font-weight: 500; transition: color 0.2s; }
        .nav-links a:hover { color: var(--primary); }
        
        .hero { text-align: center; padding: 60px 20px; }
        .hero h1 { font-size: 3rem; margin-bottom: 16px; color: #111827; }
        .hero p { font-size: 1.25rem; color: var(--text-light); max-width: 600px; margin: 0 auto; }
        
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 30px; margin-top: 40px; }
        .feature-card { background: var(--card); padding: 24px; border-radius: 12px; border: 1px solid var(--border); transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; }
        .feature-card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
        .feature-icon { font-size: 2rem; margin-bottom: 16px; display: block; }
        .feature-title { font-weight: 600; font-size: 1.1rem; margin-bottom: 8px; display: block; }
        .feature-desc { color: var(--text-light); font-size: 0.95rem; }
    </style>
</head>
<body>
    <div class="nav">
        <div class="nav-content">
            <a href="/" class="nav-logo">
                SecretCorp
            </a>
            <div class="nav-links">
                <a href="/">Home</a>
                <a href="/comments">Discussion</a>
                <a href="/profile">Profile</a>
                <a href="/search">Search</a>
                <a href="/messages">Messages</a>
                <a href="/admin">Admin</a>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="hero">
            <h1>Connect with friends</h1>
            <p>Share your thoughts, follow your interests, and discover new people on SecretCorp.</p>
        </div>
        
        <div class="features">
            <div class="feature-card" onclick="window.location.href='/search'">
                <span class="feature-icon">🔍</span>
                <span class="feature-title">Discover</span>
                <span class="feature-desc">Search for friends, posts, and trending topics across the platform.</span>
            </div>
            <div class="feature-card" onclick="window.location.href='/comments'">
                <span class="feature-icon">💬</span>
                <span class="feature-title">Discuss</span>
                <span class="feature-desc">Join conversations and share your opinions with the community.</span>
            </div>
            <div class="feature-card" onclick="window.location.href='/profile'">
                <span class="feature-icon">👤</span>
                <span class="feature-title">Personalize</span>
                <span class="feature-desc">Customize your profile and let people know who you are.</span>
            </div>
            <div class="feature-card" onclick="window.location.href='/messages'">
                <span class="feature-icon">📧</span>
                <span class="feature-title">Connect</span>
                <span class="feature-desc">Send private messages to friends and colleagues.</span>
            </div>
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
    
    search_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Search - SecretCorp</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; margin: 0; background: #f9fafb; color: #1f2937; }}
            .nav {{ background: white; padding: 0 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .nav-content {{ max-width: 1100px; margin: 0 auto; height: 64px; display: flex; align-items: center; }}
            .nav-logo {{ font-weight: 700; color: #4f46e5; text-decoration: none; margin-right: 30px; }}
            .container {{ max-width: 800px; margin: 40px auto; padding: 0 20px; }}
            .search-box {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 30px; }}
            .search-form {{ display: flex; gap: 10px; }}
            input[type="text"] {{ flex: 1; padding: 12px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 1rem; }}
            select {{ padding: 12px; border: 1px solid #e5e7eb; border-radius: 6px; background: white; }}
            button {{ background: #4f46e5; color: white; border: none; padding: 0 24px; border-radius: 6px; font-weight: 500; cursor: pointer; }}
            button:hover {{ background: #4338ca; }}
            .results-header {{ margin-bottom: 20px; }}
            .result-card {{ background: white; padding: 20px; border-radius: 8px; border: 1px solid #e5e7eb; margin-bottom: 16px; }}
            .result-title {{ font-weight: 600; margin-bottom: 4px; color: #111827; }}
            .result-meta {{ color: #6b7280; font-size: 0.875rem; }}
            .no-results {{ text-align: center; color: #6b7280; padding: 40px; }}
            .back-link {{ display: block; margin-top: 20px; color: #6b7280; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="nav">
            <div class="nav-content">
                <a href="/" class="nav-logo">SecretCorp</a>
            </div>
        </div>
        <div class="container">
            <div class="search-box">
                <form method="GET" class="search-form">
                    <input type="text" name="q" value="{query}" placeholder="Search users, posts, or topics...">
                    <select name="type">
                        <option value="all" {'selected' if filter_type == 'all' else ''}>All</option>
                        <option value="users" {'selected' if filter_type == 'users' else ''}>People</option>
                        <option value="posts" {'selected' if filter_type == 'posts' else ''}>Posts</option>
                    </select>
                    <button type="submit">Search</button>
                </form>
            </div>
            
            <div class="results">
    """
    
    if query:
        search_html += f"""
            <div class="results-header">
                <h3>Results for "{query}"</h3>
            </div>
            <div class="result-card">
                <div class="result-title">User Profile: {query}</div>
                <div class="result-meta">Found in People • {filter_type}</div>
            </div>
            <div class="result-card">
                <div class="result-title">Discussion about {query}</div>
                <div class="result-meta">Found in Posts • Posted 2 hours ago</div>
            </div>
        """
        
        search_history.append({
            'query': query,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'filter': filter_type
        })
    else:
        search_html += '<div class="no-results">Enter a keyword to start searching</div>'
    
    search_html += """
            </div>
            <a href="/" class="back-link">← Back to Home</a>
        </div>
    </body>
    </html>
    """
    
    return search_html

@app.route('/profile')
def profile_page():
    username = request.args.get('user', 'guest')
    bio = request.args.get('bio', '')
    
    profile_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{username} - Profile</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; margin: 0; background: #f3f4f6; color: #1f2937; }}
            .cover {{ height: 200px; background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); }}
            .container {{ max-width: 900px; margin: -60px auto 40px; padding: 0 20px; position: relative; }}
            .profile-card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
            .profile-header {{ padding: 30px; text-align: center; border-bottom: 1px solid #e5e7eb; }}
            .avatar {{ width: 120px; height: 120px; background: white; border-radius: 50%; margin: -90px auto 20px; display: flex; align-items: center; justify-content: center; font-size: 3rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 4px solid white; }}
            .username {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }}
            .meta {{ color: #6b7280; font-size: 0.9rem; margin-bottom: 20px; }}
            .bio-section {{ padding: 30px; }}
            .bio-content {{ background: #f9fafb; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
            .edit-section {{ border-top: 1px solid #e5e7eb; padding: 30px; background: #fafafa; }}
            textarea {{ width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 6px; margin-bottom: 10px; box-sizing: border-box; font-family: inherit; }}
            .btn {{ background: #4f46e5; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 500; }}
            .nav-link {{ display: inline-block; margin-top: 20px; color: #6b7280; text-decoration: none; margin-right: 20px; }}
        </style>
        <script>
            function updateProfile() {{
                const newBio = document.getElementById('bioInput').value;
                window.location.href = '/profile?user={username}&bio=' + encodeURIComponent(newBio);
            }}
        </script>
    </head>
    <body>
        <div class="cover"></div>
        <div class="container">
            <div class="profile-card">
                <div class="profile-header">
                    <div class="avatar">👤</div>
                    <div class="username">{username}</div>
                    <div class="meta">Member since 2024 • <span style="color: #10b981">Active</span></div>
                </div>
                
                <div class="bio-section">
                    <h3>About</h3>
                    <div class="bio-content">
                        {bio if bio else 'No bio information available.'}
                    </div>
                </div>
                
                <div class="edit-section">
                    <h3>Update Bio</h3>
                    <p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 15px;">Share something about yourself with the community.</p>
                    <textarea id="bioInput" rows="4" placeholder="Write your bio here...">{bio}</textarea>
                    <br>
                    <button class="btn" onclick="updateProfile()">Save Changes</button>
                    <br>
                    <a href="/" class="nav-link">← Home</a>
                    <a href="/profile?user=admin" class="nav-link">View Admin Profile</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return profile_html

@app.route('/comments', methods=['GET', 'POST'])
def comments_page():
    if request.method == 'POST':
        name = request.form.get('name', 'Anonymous')
        comment = request.form.get('comment', '')
        email = request.form.get('email', '')
        
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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Discussion - SecretCorp</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; margin: 0; background: #f9fafb; color: #1f2937; }
            .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
            .header { margin-bottom: 30px; }
            .comment-box { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 40px; }
            .form-group { margin-bottom: 15px; }
            input, textarea { width: 100%; padding: 12px; border: 1px solid #e5e7eb; border-radius: 6px; box-sizing: border-box; font-family: inherit; }
            button { background: #4f46e5; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: 600; }
            .comment-list { display: flex; flex-direction: column; gap: 20px; }
            .comment-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e5e7eb; }
            .comment-header { display: flex; justify-content: space-between; margin-bottom: 10px; align-items: center; }
            .author { font-weight: 600; color: #111827; }
            .time { color: #9ca3af; font-size: 0.875rem; }
            .comment-body { line-height: 1.6; color: #374151; }
            .admin-badge { background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; margin-left: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Community Discussion</h1>
                <p>Join the conversation and share your thoughts.</p>
            </div>
            
            <div class="comment-box">
                <form method="POST">
                    <div class="form-group">
                        <input type="text" name="name" placeholder="Your Name" required>
                    </div>
                    <div class="form-group">
                        <input type="email" name="email" placeholder="Your Email (optional)">
                    </div>
                    <div class="form-group">
                        <textarea name="comment" placeholder="What are you thinking?" rows="3" required></textarea>
                    </div>
                    <button type="submit">Post Comment</button>
                </form>
            </div>
            
            <div class="comment-list">
                <h3>Recent Comments (""" + str(len(comments)) + """)</h3>
    """
    
    for comment in reversed(comments[-10:]):
        is_admin = 'admin' in comment['name'].lower()
        admin_tag = '<span class="admin-badge">ADMIN</span>' if is_admin else ''
        comments_html += f"""
            <div class="comment-card" style="{ 'border-left: 4px solid #ef4444;' if is_admin else '' }">
                <div class="comment-header">
                    <div>
                        <span class="author">{comment['name']}</span>
                        {admin_tag}
                        {f'<span style="color: #9ca3af; font-size: 0.9em;">&lt;{comment["email"]}&gt;</span>' if comment['email'] else ''}
                    </div>
                    <span class="time">{comment['timestamp']}</span>
                </div>
                <div class="comment-body">{comment['comment']}</div>
            </div>
        """
    
    if not comments:
        comments_html += '<div style="text-align: center; color: #9ca3af; padding: 20px;">No comments yet. Be the first to share!</div>'
    
    comments_html += """
            </div>
            <div style="margin-top: 30px;">
                <a href="/" style="color: #6b7280; text-decoration: none;">← Back to Home</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return comments_html

@app.route('/messages')
def messages_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Messages - SecretCorp</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; margin: 0; background: #f3f4f6; height: 100vh; display: flex; flex-direction: column; }
            .nav { background: white; padding: 0 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
            .nav-content { max-width: 1100px; margin: 0 auto; height: 64px; display: flex; align-items: center; }
            .back-link { color: #6b7280; text-decoration: none; font-weight: 500; }
            
            .main { flex: 1; max-width: 1000px; margin: 20px auto; width: 100%; display: grid; grid-template-columns: 300px 1fr; gap: 20px; padding: 0 20px; box-sizing: border-box; }
            
            .sidebar { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); height: calc(100vh - 140px); overflow-y: auto; }
            .msg-area { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); height: calc(100vh - 140px); display: flex; flex-direction: column; }
            
            .compose-box { margin-top: auto; border-top: 1px solid #e5e7eb; padding-top: 20px; }
            input, textarea { width: 100%; padding: 12px; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 10px; box-sizing: border-box; font-family: inherit; }
            .btn { background: #4f46e5; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 500; margin-right: 10px; }
            .btn-outline { background: white; border: 1px solid #d1d5db; color: #374151; }
            
            .message-bubble { background: #f3f4f6; padding: 15px; border-radius: 12px; margin-bottom: 15px; border-left: 4px solid #4f46e5; }
            .preview-box { background: #fffbeb; border: 1px solid #fcd34d; padding: 15px; border-radius: 8px; margin-bottom: 15px; display: none; }
        </style>
    </head>
    <body>
        <div class="nav">
            <div class="nav-content">
                <a href="/" class="back-link">← Back to SecretCorp</a>
            </div>
        </div>
        
        <div class="main">
            <div class="sidebar">
                <h3 style="margin-top: 0;">Inbox</h3>
                <div class="message-bubble">
                    <strong>System</strong><br>
                    <span style="font-size: 0.9em; color: #666;">Welcome to your messages!</span>
                </div>
                <div id="messagesList"></div>
            </div>
            
            <div class="msg-area">
                <div id="preview" class="preview-box">
                    <strong>Preview:</strong>
                    <div id="previewContent"></div>
                </div>
                
                <div class="compose-box">
                    <h3>New Message</h3>
                    <input type="text" id="recipientInput" placeholder="To: (username)">
                    <input type="text" id="subjectInput" placeholder="Subject">
                    <textarea id="messageInput" rows="3" placeholder="Type your message..."></textarea>
                    <div style="margin-top: 10px;">
                        <button class="btn" onclick="sendMessage()">Send</button>
                        <button class="btn btn-outline" onclick="previewMessage()">Preview</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function previewMessage() {
                const recipient = document.getElementById('recipientInput').value;
                const subject = document.getElementById('subjectInput').value;
                const message = document.getElementById('messageInput').value;
                
                const previewDiv = document.getElementById('preview');
                const previewContent = document.getElementById('previewContent');
                
                previewContent.innerHTML = `
                    <strong>To:</strong> ${recipient}<br>
                    <strong>Subject:</strong> ${subject}<br>
                    <strong>Message:</strong><br>
                    <div style="margin-top: 5px;">${message}</div>
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
                
                const messagesList = document.getElementById('messagesList');
                const newMessage = document.createElement('div');
                newMessage.className = 'message-bubble';
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
            
            window.onload = function() {
                const hash = window.location.hash.substring(1);
                if (hash) {
                    const params = new URLSearchParams(hash);
                    const autoFillMsg = params.get('msg');
                    const autoFillRecipient = params.get('to');
                    
                    if (autoFillMsg) {
                        document.getElementById('messageInput').value = decodeURIComponent(autoFillMsg);
                    }
                    if (autoFillRecipient) {
                        document.getElementById('recipientInput').value = decodeURIComponent(autoFillRecipient);
                    }
                }
            };
        </script>
    </body>
    </html>
    """

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    
    results_html = f"""
        <div class="search-results">
            <h4>Results for: {query}</h4>
    """
    
    if query:
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
        'html': results_html
    })

@app.route('/api/profile/<username>')
def api_profile(username):
    bio = request.args.get('bio', f'This is {username}\'s profile')
    
    return jsonify({
        'username': username,
        'bio': bio,
        'html_bio': f'<div class="bio">{bio}</div>',
        'status': 'active'
    })

@app.route('/admin')
def admin_panel():
    session_id = request.args.get('session', '')
    debug_info = request.args.get('debug', '')
    
    admin_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Admin - SecretCorp</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; margin: 0; background: #f3f4f6; color: #1f2937; }}
            .sidebar {{ width: 250px; background: #1f2937; height: 100vh; position: fixed; color: white; padding: 20px; box-sizing: border-box; }}
            .main {{ margin-left: 250px; padding: 30px; }}
            .brand {{ font-size: 1.25rem; font-weight: 700; margin-bottom: 40px; display: block; color: white; text-decoration: none; }}
            .menu-item {{ display: block; color: #9ca3af; text-decoration: none; padding: 10px 0; transition: color 0.2s; }}
            .menu-item:hover {{ color: white; }}
            .menu-item.active {{ color: white; font-weight: 600; }}
            
            .card {{ background: white; border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; }}
            .card-header {{ margin-bottom: 20px; border-bottom: 1px solid #e5e7eb; padding-bottom: 10px; }}
            h2 {{ margin: 0; font-size: 1.1rem; }}
            
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #e5e7eb; }}
            th {{ color: #6b7280; font-weight: 500; font-size: 0.875rem; }}
            
            .debug-box {{ background: #fee2e2; border: 1px solid #fecaca; color: #991b1b; padding: 15px; border-radius: 6px; font-family: monospace; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <a href="/" class="brand">SecretCorp Admin</a>
            <a href="#" class="menu-item active">Dashboard</a>
            <a href="#" class="menu-item">Users</a>
            <a href="#" class="menu-item">Settings</a>
            <a href="/" class="menu-item" style="margin-top: auto;">← Back to Site</a>
        </div>
        
        <div class="main">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
                <h1 style="margin: 0;">Dashboard</h1>
                {f'<span>Session ID: {session_id}</span>' if session_id else ''}
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2>System Statistics</h2>
                </div>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Total Comments</td><td>{len(comments)}</td></tr>
                    <tr><td>Search Queries</td><td>{len(search_history)}</td></tr>
                    <tr><td>Active Sessions</td><td>1</td></tr>
                </table>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <h2>Recent Activity</h2>
                </div>
                <div style="margin-bottom: 20px;">
                    <h3 style="font-size: 1rem; color: #4b5563;">Latest Comments</h3>
    """
    
    for comment in comments[-5:]:
        admin_html += f"""
            <div style="padding: 10px 0; border-bottom: 1px solid #f3f4f6;">
                <strong>{comment['name']}</strong>: {comment['comment']}
                <div style="font-size: 0.8rem; color: #9ca3af;">{comment['timestamp']}</div>
            </div>
        """
    
    admin_html += """
                </div>
                <div>
                    <h3 style="font-size: 1rem; color: #4b5563;">Recent Searches</h3>
    """
    
    for search in search_history[-5:]:
        admin_html += f"""
            <div style="padding: 8px 0; border-bottom: 1px solid #f3f4f6;">
                Search: <strong>{search['query']}</strong> 
                <span style="color: #9ca3af; font-size: 0.9em;">({search['filter']})</span>
            </div>
        """
    
    if debug_info:
        admin_html += f"""
            <div style="margin-top: 20px;">
                <div class="debug-box">
                    <strong>Debug Output:</strong> {debug_info}
                </div>
            </div>
        """
    
    admin_html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    return admin_html

@app.route('/widget')
def widget():
    title = request.args.get('title', 'Widget')
    callback = request.args.get('callback', '')
    config = request.args.get('config', '{}')
    
    widget_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }}
            .widget-box {{ border: 1px solid #e5e7eb; padding: 20px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            h3 {{ margin-top: 0; color: #1f2937; }}
            code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
        </style>
        <script>
            var widgetConfig = {config};
            var widgetTitle = "{title}";
            
            function initWidget() {{
                console.log("Widget loaded: " + widgetTitle);
                {f'{callback}();' if callback else ''}
            }}
            
            window.onload = initWidget;
        </script>
    </head>
    <body>
        <div class="widget-box" title="{title}">
            <h3>{title}</h3>
            <p>Widget Configuration Loaded.</p>
            <p>Config: <code>{config}</code></p>
        </div>
    </body>
    </html>
    """
    
    return widget_html

if __name__ == '__main__':
    print("Starting SecretCorp Application...")
    print("Server running on http://0.0.0.0:5011")
    app.run(host='0.0.0.0', port=5011, debug=True)
