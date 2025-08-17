from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import os
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey123'

USER_FILE = 'users.txt'
GUIDES_DIR = 'guides'
UPLOADS_DIR = 'static/uploads'

# Create folders if not exist
os.makedirs(GUIDES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

def read_users():
    users = {}
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            for line in f:
                if ':' in line:
                    username, password = line.strip().split(':', 1)
                    users[username] = password
    return users

def write_user(username, password):
    with open(USER_FILE, 'a') as f:
        f.write(f"{username}:{password}\n")

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']                                                                                                                     password = request.form['password']
        users = read_users()
        if username in users and users[username] == password:
            session['username'] = username
            flash("Logged in successfully!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template('register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template('register.html')

        if not re.match("^[a-zA-Z0-9_]+$", username):
            flash("Username can only contain letters, numbers, and underscore.", "error")
            return render_template('register.html')

        users = read_users()
        if username in users:
            flash("Username already exists.", "error")
            return render_template('register.html')

        write_user(username, password)
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    guides = []
    for f in os.listdir(GUIDES_DIR):
        if f.startswith(f"{username}_") and f.endswith(".html"):
            title = f.replace(f"{username}_", "").replace(".html", "").replace("_", " ").title()
            guides.append({
                'title': title,
                'url': url_for('view_guide', filename=f)
            })
    return render_template('dashboard.html', guides=guides)

@app.route('/create', methods=['GET', 'POST'])
def create_guide():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content']
        image_files = request.files.getlist('image_file')

        if not title:
            flash("Title is required.", "error")
            return render_template('create_guide.html', content=content)

        # Save uploaded images
        image_urls = []
        for img in image_files:
            if img and img.filename != '':
                # Sanitize filename
                ext = os.path.splitext(img.filename)[1]
                if ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    flash(f"Skipped unsupported image: {img.filename}", "error")
                    continue

                safe_name = f"{session['username']}_{hash(img.filename)}{ext}"
                path = os.path.join(UPLOADS_DIR, safe_name)
                img.save(path)
                image_urls.append(f"/static/uploads/{safe_name}")

        # Generate safe filename for guide
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
        filename = f"{session['username']}_{safe_title.replace(' ', '_')}.html"
        filepath = os.path.join(GUIDES_DIR, filename)

        # Generate HTML for guide
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        img {{ max-width: 100%; height: auto; margin: 15px 0; border-radius: 8px; }}
        .footer {{ margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 0.9em; }}
        a {{ color: #3498db; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p><em>By {session['username']} | {datetime.now().strftime('%B %d, %Y')}</em></p>
        {''.join(f'<img src="{url}" alt="User image">' for url in image_urls)}
        <div style="line-height: 1.8; margin-top: 20px;">
            {content.replace(chr(10), '<br>')}
        </div>
        <div class="footer">
            <hr>
            <a href="/dashboard">← Back to Dashboard</a>
        </div>
    </div>
</body>
</html>'''

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        flash("Guide created successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('create_guide.html')

# ✅ Fix: Serve guides properly
@app.route('/guides/<filename>')
def view_guide(filename):
    return send_from_directory(GUIDES_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
