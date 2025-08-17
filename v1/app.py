from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
import os
import re
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey123'

USER_FILE = 'users.txt'
GUIDES_DIR = 'guides'
UPLOADS_DIR = 'static/uploads'
REACTIONS_FILE = 'reactions.json'

# Vytvor priečinky, ak neexistujú
os.makedirs(GUIDES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Vytvor reactions.json, ak neexistuje
if not os.path.exists(REACTIONS_FILE):
    with open(REACTIONS_FILE, 'w') as f:
        json.dump({}, f)

# Zoznam kategórií
CATEGORIES = ["Woodworking", "Cooking", "Electronics", "Gardening", "DIY Home", "Other"]

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
        username = request.form['username']
        password = request.form['password']
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

    guides = []
    for f in os.listdir(GUIDES_DIR):
        if f.endswith(".html"):
            parts = f.split('_', 1)
            if len(parts) < 2:
                continue
            author = parts[0]
            title = parts[1].replace(".html", "").replace("_", " ").title()

            filepath = os.path.join(GUIDES_DIR, f)
            category = "Other"

            try:
                with open(filepath, encoding='utf-8') as ff:
                    content = ff.read()
                    if "Category: Woodworking" in content:
                        category = "Woodworking"
                    elif "Category: Cooking" in content:
                        category = "Cooking"
                    elif "Category: Electronics" in content:
                        category = "Electronics"
                    elif "Category: Gardening" in content:
                        category = "Gardening"
                    elif "Category: DIY Home" in content:
                        category = "DIY Home"
            except:
                pass

            try:
                created_time = os.path.getctime(filepath)
            except:
                created_time = 0

            guides.append({
                'title': title,
                'author': author,
                'url': url_for('view_guide', filename=f),
                'filename': f,
                'category': category,
                'created_time': created_time
            })

    guides.sort(key=lambda x: x['created_time'], reverse=True)

    return render_template('dashboard.html', guides=guides, categories=CATEGORIES)

@app.route('/create', methods=['GET', 'POST'])
def create_guide():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content']
        category = request.form['category']
        image_files = request.files.getlist('image_file')

        if not title:
            flash("Title is required.", "error")
            return render_template('create_guide.html', content=content, categories=CATEGORIES)

        if category not in CATEGORIES:
            flash("Invalid category.", "error")
            return render_template('create_guide.html', content=content, categories=CATEGORIES)

        # Ulož obrázky
        image_urls = []
        for img in image_files:
            if img and img.filename != '':
                ext = os.path.splitext(img.filename)[1]
                if ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    flash(f"Skipped unsupported image: {img.filename}", "error")
                    continue

                safe_name = f"{session['username']}_{hash(img.filename)}{ext}"
                path = os.path.join(UPLOADS_DIR, safe_name)
                img.save(path)
                image_urls.append(f"/static/uploads/{safe_name}")

        # Vygeneruj názov súboru
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
        filename = f"{session['username']}_{safe_title.replace(' ', '_')}.html"
        filepath = os.path.join(GUIDES_DIR, filename)

        # Ulož pre JS
        context_filename = filename

        # Vygeneruj HTML
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        h1 {{ 
            color: #2c3e50; 
            border-bottom: 2px solid #3498db; 
            padding-bottom: 10px; 
            text-align: center; 
        }}
        .meta {{ 
            font-size: 0.9em; 
            color: #7f8c8d; 
            margin-bottom: 20px; 
            text-align: center; 
        }}
        .guide-image {{ 
            width: 50%; 
            height: auto; 
            margin: 15px 0; 
            border-radius: 8px; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.1); 
        }}
        .footer {{ margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 0.9em; }}
        a {{ color: #3498db; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="meta">
            By {session['username']} | Category: {category} | {datetime.now().strftime('%B %d, %Y')}
        </p>
        {''.join(f'<img src="{url}" alt="User image" class="guide-image">' for url in image_urls)}
        <div style="line-height: 1.8; margin-top: 20px;">
            {content.replace(chr(10), '<br>')}
        </div>

        <!-- Reactions / Emoji -->
        <div class="reactions" style="margin: 30px 0; text-align: center;">
            <p style="font-size: 18px; color: #2c3e50; margin-bottom: 10px;">React to this guide:</p>
            <div id="emoji-container" style="font-size: 28px; margin: 10px 0;">
                <span class="emoji-btn" data-emoji="👍" style="cursor: pointer; margin: 0 10px;">👍</span>
                <span class="emoji-btn" data-emoji="❤️" style="cursor: pointer; margin: 0 10px;">❤️</span>
                <span class="emoji-btn" data-emoji="🛠️" style="cursor: pointer; margin: 0 10px;">🛠️</span>
                <span class="emoji-btn" data-emoji="🚀" style="cursor: pointer; margin: 0 10px;">🚀</span>
            </div>
            <div id="reaction-counts" style="margin-top: 10px; font-size: 14px; color: #7f8c8d;">
                Loading reactions...
            </div>
            <div id="reaction-message" style="margin-top: 10px; font-size: 14px; color: #e74c3c; display: none;"></div>
        </div>

        <script>
        const guideFilename = "{context_filename}";
        const currentUser = "{session['username']}";
        let userReaction = null;

        async function loadReactions() {{
            try {{
                const res = await fetch(`/get_reactions/${{guideFilename}}`);
                const data = await res.json();
                updateReactionUI(data.counts, data.userReaction);
                userReaction = data.userReaction;
                if (userReaction) {{
                    disableEmojis();
                }}
            }} catch (e) {{
                document.getElementById('reaction-counts').textContent = "Failed to load reactions.";
            }}
        }}

        function updateReactionUI(counts, userReaction) {{
            const container = document.getElementById('reaction-counts');
            let html = '';
            for (const [emoji, count] of Object.entries(counts)) {{
                html += `<span style="margin: 0 8px;"><b>${{emoji}}</b>: ${{count}}</span> `;
            }}
            container.innerHTML = html || 'No reactions yet.';
        }}

        function disableEmojis() {{
            document.querySelectorAll('.emoji-btn').forEach(btn => {{
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
            }});
        }}

        async function addReaction(emoji) {{
            if (userReaction) return;

            const res = await fetch(`/add_reaction/${{guideFilename}}/${{emoji}}`, {{
                method: 'POST'
            }});

            const data = await res.json();

            if (data.success) {{
                userReaction = emoji;
                disableEmojis();
                updateReactionUI(data.counts, emoji);
            }} else if (data.error === 'Already reacted') {{
                document.getElementById('reaction-message').style.display = 'block';
                document.getElementById('reaction-message').textContent = 'You already reacted to this guide.';
                setTimeout(() => {{
                    document.getElementById('reaction-message').style.display = 'none';
                }}, 3000);
            }} else {{
                document.getElementById('reaction-message').textContent = 'Error saving reaction.';
                document.getElementById('reaction-message').style.display = 'block';
            }}
        }}

        document.querySelectorAll('.emoji-btn').forEach(btn => {{
            btn.addEventListener('click', (e) => {{
                if (!userReaction) {{
                    e.target.style.transform = 'scale(1.3)';
                    setTimeout(() => e.target.style.transform = 'scale(1)', 150);
                    addReaction(e.target.dataset.emoji);
                }}
            }});
        }});

        loadReactions();
        </script>

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

    return render_template('create_guide.html', categories=CATEGORIES)

@app.route('/get_reactions/<filename>')
def get_reactions(filename):
    guide_id = filename
    try:
        with open(REACTIONS_FILE, 'r') as f:
            reactions = json.load(f)
    except:
        reactions = {}

    counts = {'👍': 0, '❤️': 0, '🛠️': 0, '🚀': 0}
    user_reaction = None

    if guide_id in reactions:
        for user, emoji in reactions[guide_id].items():
            if emoji in counts:
                counts[emoji] += 1
        user_reaction = reactions[guide_id].get(session.get('username'))

    return jsonify({'counts': counts, 'userReaction': user_reaction})

@app.route('/add_reaction/<filename>/<emoji>', methods=['POST'])
def add_reaction(filename, emoji):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    guide_path = os.path.join(GUIDES_DIR, filename)
    if not os.path.exists(guide_path):
        return jsonify({'error': 'Guide not found'}), 404

    try:
        with open(REACTIONS_FILE, 'r') as f:
            reactions = json.load(f)
    except:
        reactions = {}

    guide_id = filename
    user = session['username']

    if guide_id in reactions and user in reactions[guide_id]:
        return jsonify({'error': 'Already reacted'}), 400

    if guide_id not in reactions:
        reactions[guide_id] = {}
    reactions[guide_id][user] = emoji

    with open(REACTIONS_FILE, 'w') as f:
        json.dump(reactions, f, indent=2)

    counts = {'👍': 0, '❤️': 0, '🛠️': 0, '🚀': 0}
    for e in reactions[guide_id].values():
        if e in counts:
            counts[e] += 1

    return jsonify({'success': True, 'counts': counts})

@app.route('/delete/<filename>')
def delete_guide(filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    filepath = os.path.join(GUIDES_DIR, filename)
    if not os.path.exists(filepath):
        flash("Guide not found.", "error")
        return redirect(url_for('dashboard'))

    if not filename.startswith(f"{session['username']}_"):
        flash("You can only delete your own guides.", "error")
        return redirect(url_for('dashboard'))

    try:
        os.remove(filepath)
        flash("Guide deleted successfully.", "success")
    except Exception as e:
        flash("Error deleting guide.", "error")

    return redirect(url_for('dashboard'))

@app.route('/guides/<filename>')
def view_guide(filename):
    return send_from_directory(GUIDES_DIR, filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True, port=5004)
