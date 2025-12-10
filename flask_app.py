from flask import Flask, render_template_string, redirect, url_for, request, session, Response, flash
import subprocess
import os
import signal
import threading
import sqlite3
import time
import csv
import io
from datetime import datetime, timedelta

app = Flask(__name__)

# --- SÉCURITÉ & CONFIGURATION ---
app.secret_key = 'CLE_SECRETE'
DB_PATH = 'VOTRE_DB'

# --- IDENTIFIANTS ADMIN ---
ADMIN_USER = "ID_ADMIN"
ADMIN_PASS = "MDP_ADMIN"

# --- ÉTAT DU BOT ---
status = {
    "running": False,
    "process": None,
    "script_name": None,
    "live_output": [],
    "last_activity": None
}

# --- LISTE DES SCRIPTS ---
SCRIPTS = {
    "EXEMPLE": "/home/PSEUDO/EXEMPLE.py"
}

# --- GESTION BASE DE DONNÉES ---
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT,
                      script TEXT,
                      message TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings
                     (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('lock_launch', '0')")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur DB Init: {e}")

def get_setting(key):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key=?", (key,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None

def set_setting(key, value):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur DB Settings: {e}")

def log_to_db(script_name, message):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO logs (date, script, message) VALUES (?, ?, ?)",
                  (timestamp, script_name, message))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur DB Insert: {e}")

init_db()

# --- GESTION PROCESSUS & MONITORING ---
def monitor_inactivity(process, script_name):
    """Surveille si le bot est inactif depuis plus de 2 heures"""
    TIMEOUT_SECONDS = 7200 # 2 heures

    while process.poll() is None:
        if status["last_activity"]:
            time_since_last = (datetime.now() - status["last_activity"]).total_seconds()

            if time_since_last > TIMEOUT_SECONDS:
                try:
                    os.kill(process.pid, signal.SIGTERM)
                    msg = f"--- ARRÊT AUTOMATIQUE : Inactivité détectée depuis {time_since_last/3600:.1f} heures ---"
                    status["live_output"].append(msg)
                    log_to_db("SYSTEM", f"Arrêt auto (Timeout 2h) pour {script_name}")

                    status["running"] = False
                    status["script_name"] = None
                    status["process"] = None
                except Exception as e:
                    print(f"Erreur arrêt auto: {e}")
                break
        time.sleep(60)

def read_output(process, script_name):
    status["last_activity"] = datetime.now()
    for line in iter(process.stdout.readline, ''):
        cleaned_line = line.strip()
        if cleaned_line:
            status["last_activity"] = datetime.now()
            status["live_output"].append(cleaned_line)
            log_to_db(script_name, cleaned_line)
    process.stdout.close()

# --- FILTRAGE LOGS ---
def get_filtered_logs(request_args, limit=500, select_columns="*"):
    f_script = request_args.get('script')
    f_date = request_args.get('date')
    f_hour = request_args.get('hour')
    f_search = request_args.get('search')

    query = f"SELECT {select_columns} FROM logs WHERE 1=1"
    params = []

    if f_script:
        query += " AND script = ?"
        params.append(f_script)

    if f_date:
        if f_hour:
            query += " AND date LIKE ?"
            params.append(f"{f_date} {f_hour}%")
        else:
            query += " AND date LIKE ?"
            params.append(f"{f_date}%")
    elif f_hour:
         query += " AND substr(date, 12, 2) = ?"
         params.append(f_hour)

    if f_search:
        query += " AND message LIKE ?"
        params.append(f"%{f_search}%")

    query += f" ORDER BY id DESC LIMIT {limit}"

    rows = []
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
    except Exception as e:
        rows = [(0, "Erreur", "Système", str(e))]
    return rows

# --- CSS PARTAGÉ ---
GLASS_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    body { font-family: 'Poppins', sans-serif; margin: 0; padding: 0; min-height: 100vh; background: linear-gradient(120deg, #0093E9 0%, #80D0C7 100%); background-size: 200% 200%; animation: gradientBG 15s ease infinite; color: #fff; }
    @keyframes gradientBG { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    .container { max-width: 900px; margin: 40px auto; padding: 20px; }
    .glass-panel { background: rgba(255, 255, 255, 0.15); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.20); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.18); padding: 30px; margin-bottom: 25px; text-align: center; }
    h1 { margin-top: 0; font-size: 2em; text-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h2, h3 { margin: 0 0 15px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .flex-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
    .filter-group { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; background: rgba(0,0,0,0.1); padding: 15px; border-radius: 10px; margin-top: 20px; }
    .btn { padding: 12px 30px; font-size: 16px; font-weight: 600; border-radius: 50px; cursor: pointer; border: none; transition: 0.3s; text-decoration: none; display: inline-block; margin: 5px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); text-align: center; }
    .btn-action { background: linear-gradient(45deg, #11998e, #38ef7d); color: white; }
    .btn-danger { background: linear-gradient(45deg, #ff416c, #ff4b2b); color: white; }
    .btn-nav { background: rgba(255,255,255,0.3); color: white; border: 1px solid rgba(255,255,255,0.4); }
    .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); }
    input, select { padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.3); background: rgba(255,255,255,0.1); color: #fff; outline: none; font-family: inherit; font-size: 16px; }
    option { background: #333; color: white; }
    .console-window { background: rgba(0, 0, 0, 0.6); border-radius: 12px; padding: 15px; height: 350px; overflow-y: scroll; text-align: left; font-family: 'Courier New', monospace; font-size: 13px; border: 1px solid rgba(255,255,255,0.1); color: #0f0; }
    .table-container { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; min-width: 600px; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
    th { background: rgba(0,0,0,0.2); color: #80D0C7; }
    .status-indicator { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; text-transform: uppercase; font-size: 0.8em; background: rgba(0,0,0,0.2); }
    .footer-link { margin-top: 30px; font-size: 0.9em; opacity: 0.7; text-align: center; }
    .footer-link a { color: white; text-decoration: none; border-bottom: 1px dashed white; }
    .footer-link a:hover { opacity: 1; border-bottom: 1px solid white; }
    .alert { background: rgba(255, 200, 0, 0.3); padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid orange; text-align: left; color: white; }
    @media screen and (max-width: 768px) {
        .container { margin: 10px auto; padding: 10px; width: 95%; max-width: 100%; box-sizing: border-box; }
        .glass-panel { padding: 20px 15px; }
        h1 { font-size: 1.5em; }
        .flex-row, .filter-group { flex-direction: column; align-items: stretch; gap: 15px; }
        .btn, input, select { width: 100%; margin: 5px 0; box-sizing: border-box; }
        .console-window { height: 250px; font-size: 11px; }
        table { font-size: 0.8em; }
    }
</style>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BOT_NAME - Dashboard</title>
  {{ glass_css|safe }}
</head>
<body>
  <div class="container">
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert">
        {% for message in messages %}{{ message }}<br>{% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <div class="glass-panel">
        <h1>BOT_NAME Dashboard</h1>
        <div class="status-indicator">
            {{ '🟢 EN COURS : ' + script_name if running else '🔴 Arrêté' }}
        </div>
    </div>

    <div class="glass-panel">
        {% if running %}
            <h3>BOT_NAME est actif</h3>
            <p style="font-size:0.8em; opacity:0.8;">Surveillance active : arrêt auto après 2h d'inactivité.</p>
            <form action="{{ url_for('stop_script') }}" method="post">
                <button class="btn btn-danger" type="submit">Arrêter BOT_NAME</button>
            </form>
        {% else %}
            {% if locked == '1' %}
                <div style="background: rgba(255,0,0,0.2); padding: 20px; border-radius: 10px; border: 1px solid rgba(255,0,0,0.4);">
                    <h3>⛔ Accès restreint</h3>
                    <p>Impossible de lancer le bot, l'admin a verrouillé le site.</p>
                </div>
            {% else %}
                <h3>Lancer un script</h3>
                <form action="{{ url_for('start_script') }}" method="POST">
                    <div class="flex-row" style="justify-content: center; gap: 10px;">
                        <select name="choice" style="min-width: 200px;">
                            <option value="Uncategorized">Uncategorized</option>
                            <option value="Orphan">Orphan</option>
                            <option value="Interwiki-EN">Interwiki-EN</option>
                            <option value="NoCats">NoCats</option>
                        </select>
                        <button class="btn btn-action" type="submit">DÉMARRER</button>
                    </div>
                </form>
            {% endif %}
        {% endif %}
    </div>

    <div class="glass-panel" style="text-align: left;">
        <div class="flex-row" style="margin-bottom: 10px;">
            <h3 style="margin:0;">Console</h3>
            <a href="{{ url_for('history') }}" class="btn btn-nav">📂 Logs</a>
        </div>
        <div class="console-window" id="logBox">
            {% for line in logs %}
                <div>{{ line }}</div>
            {% endfor %}
        </div>
    </div>

    <div class="footer-link">
        <a href="{{ url_for('login') }}">⚙️ Paramètres Admin</a>
    </div>
  </div>
  <script>
    var logBox = document.getElementById("logBox");
    logBox.scrollTop = logBox.scrollHeight;
    setInterval(function(){
        fetch("/api/live_logs")
        .then(r => r.text())
        .then(data => {
            let oldScroll = logBox.scrollTop;
            let isScrolledToBottom = logBox.scrollHeight - logBox.clientHeight <= logBox.scrollTop + 20;
            logBox.innerHTML = data;
            if(isScrolledToBottom) logBox.scrollTop = logBox.scrollHeight;
        });
    }, 2000);
  </script>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Admin Login - BOT_NAME</title>
  {{ glass_css|safe }}
</head>
<body>
  <div class="container" style="max-width: 400px; margin-top: 100px;">
    <div class="glass-panel">
        <h2>🔒 Connexion Admin</h2>
        {% if error %}
            <div style="color: #ffcccc; margin-bottom: 10px;">{{ error }}</div>
        {% endif %}
        <form action="{{ url_for('login') }}" method="POST">
            <input type="text" name="username" placeholder="Identifiant" required style="width: 100%; margin-bottom: 10px; box-sizing: border-box;">
            <input type="password" name="password" placeholder="Mot de passe" required style="width: 100%; margin-bottom: 20px; box-sizing: border-box;">
            <button class="btn btn-action" type="submit" style="width: 100%;">Se connecter</button>
        </form>
        <br>
        <a href="{{ url_for('index') }}" class="btn btn-nav">Retour Accueil</a>
    </div>
  </div>
</body>
</html>
"""

SETTINGS_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Paramètres - BOT_NAME</title>
  {{ glass_css|safe }}
</head>
<body>
  <div class="container" style="max-width: 600px;">
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="alert">
        {% for message in messages %}{{ message }}<br>{% endfor %}
        </div>
      {% endif %}
    {% endwith %}
    <div class="glass-panel">
        <h1>⚙️ Paramètres Admin</h1>
        <p>Connecté en tant que <b>{{ session['user'] }}</b></p>
    </div>

    <div class="glass-panel" style="text-align: left;">
        <h3>🧹 Maintenance des Logs</h3>
        <form action="{{ url_for('cleanup_logs') }}" method="POST">
            <p style="margin-bottom: 15px;">Supprimer les logs plus anciens que (jours) :</p>
            <div style="display:flex; gap:10px; align-items:center;">
                <input type="number" name="days" value="50" min="1" required
                       style="width:100px; display:inline-block; margin-bottom: 0;">
                <span style="font-size: 1.1em; color: #ccc;">jours.</span>
                <button class="btn btn-danger" type="submit" style="flex-grow: 1; margin:0;">Nettoyer</button>
            </div>
            <p style="font-size: 0.9em; opacity: 0.8; margin-top: 10px;">Attention : Suppression définitive.</p>
        </form>
    </div>

    <div class="glass-panel" style="text-align: left;">
        <h3>Sécurité du site</h3>
        <form action="{{ url_for('update_settings') }}" method="POST">
            <div style="margin-bottom: 20px;">
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" name="lock_launch" value="1"
                    {% if locked == '1' %}checked{% endif %}
                    style="width: 25px; height: 25px; margin-right: 15px;">
                    <span style="font-size: 1.1em;">
                        Verrouiller le lancement (Empêcher le démarrage des bots depuis l'accueil)
                    </span>
                </label>
            </div>
            <button class="btn btn-action" type="submit">Enregistrer les modifications</button>
        </form>
    </div>

    <div style="text-align: center;">
        <a href="{{ url_for('logout') }}" class="btn btn-danger">Se déconnecter</a>
        <a href="{{ url_for('index') }}" class="btn btn-nav">Retour Dashboard</a>
    </div>
  </div>
</body>
</html>
"""

HISTORY_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Historique - BOT_NAME</title>
  {{ glass_css|safe }}
</head>
<body>
  <div class="container" style="max-width: 1100px;">
    <div class="glass-panel" style="text-align: left;">
        <div class="flex-row">
            <h2>📂 Logs</h2>
            <form id="export-form" style="display:flex; gap:10px; align-items:center;">
                <select id="export-format" style="width:100px; padding: 5px; margin:0;">
                    <option value="txt">TXT</option>
                    <option value="csv">CSV</option>
                </select>
                <button type="submit" class="btn btn-action" style="margin:0;">⬇️ Exporter</button>
            </form>
            <a href="{{ url_for('index') }}" class="btn btn-nav">← Retour</a>
        </div>

        <form id="filter-form" action="{{ url_for('history') }}" method="GET">
            <div class="filter-group">
                <select name="script">
                    <option value="">-- Tous les scripts --</option>
                    {% for s in scripts_list %}
                        <option value="{{ s }}" {{ 'selected' if request.args.get('script') == s else '' }}>{{ s }}</option>
                    {% endfor %}
                </select>

                <input type="date" name="date" value="{{ request.args.get('date', '') }}">

                <select name="hour">
                    <option value="">-- Heure --</option>
                    {% for h in range(0, 24) %}
                        {% set h_str = '%02d' % h %}
                        <option value="{{ h_str }}" {{ 'selected' if request.args.get('hour') == h_str else '' }}>{{ h_str }}h</option>
                    {% endfor %}
                </select>

                <input type="text" name="search" placeholder="Mot clé..." value="{{ request.args.get('search', '') }}" style="flex-grow: 1;">

                <button type="submit" class="btn btn-action" style="margin:0;">🔍 Filtrer</button>
                <a href="{{ url_for('history') }}" class="btn btn-nav" style="margin:0;">Reset</a>
            </div>
        </form>

        <div class="table-container">
            <table>
                <tr>
                    <th style="width: 180px;">Date & Heure</th>
                    <th style="width: 150px;">Script</th>
                    <th>Message</th>
                </tr>
                {% if rows %}
                    {% for row in rows %}
                    <tr>
                        <td style="font-family:monospace; color: #a8dadc;">{{ row[1] }}</td>
                        <td><span style="background:rgba(255,255,255,0.1); padding:2px 8px; border-radius:4px;">{{ row[2] }}</span></td>
                        <td>{{ row[3] }}</td>
                    </tr>
                    {% endfor %}
                {% else %}
                    <tr>
                        <td colspan="3" style="text-align:center; padding: 20px;">Aucun log trouvé.</td>
                    </tr>
                {% endif %}
            </table>
        </div>
    </div>
  </div>

  <script>
    document.getElementById('export-form').addEventListener('submit', function(event) {
        event.preventDefault();
        const format = document.getElementById('export-format').value;
        const formFilter = document.getElementById('filter-form');
        const params = new URLSearchParams();
        formFilter.querySelectorAll('select, input[type="date"], input[type="text"]').forEach(input => {
            if (input.value) { params.append(input.name, input.value); }
        });
        params.append('format', format);
        window.location.href = "{{ url_for('export_logs') }}?" + params.toString();
    });
  </script>
</body>
</html>
"""

# --- ROUTES FLASK ---

@app.route("/")
def index():
    locked = get_setting('lock_launch')
    return render_template_string(
        DASHBOARD_HTML,
        running=status["running"],
        script_name=status.get("script_name") or "Inactif",
        logs=status["live_output"][-50:],
        locked=locked,
        glass_css=GLASS_CSS
    )

@app.route("/api/live_logs")
def live_logs():
    return "\n".join([f"<div>{line}</div>" for line in status["live_output"][-100:]])

@app.route("/history")
def history():
    rows = get_filtered_logs(request.args, limit=500, select_columns="id, date, script, message")
    return render_template_string(HISTORY_HTML, rows=rows, scripts_list=SCRIPTS.keys(), request=request, glass_css=GLASS_CSS)

@app.route("/export")
def export_logs():
    rows = get_filtered_logs(request.args, limit=10000, select_columns="date, script, message")
    fmt = request.args.get('format', 'txt')
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == 'csv':
        si = io.StringIO()
        cw = csv.writer(si, delimiter=';')
        cw.writerow(['Date', 'Script', 'Message'])
        for row in rows: cw.writerow(row)
        output = si.getvalue()
        mimetype = 'text/csv'
        filename = f"logs_BOT_NAME_{now}.csv"
    else:
        output = "Date et Heure\tScript\tMessage\n"
        for row in rows:
            message = row[2].replace('\n', ' ')
            output += f"{row[0]}\t{row[1]}\t{message}\n"
        mimetype = 'text/plain'
        filename = f"logs_BOT_NAME_{now}.txt"

    response = Response(output, mimetype=mimetype)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

@app.route("/start", methods=["POST"])
def start_script():
    if get_setting('lock_launch') == '1':
        return redirect(url_for("index"))

    if not status["running"]:
        choice = request.form.get("choice")
        path = SCRIPTS.get(choice)
        if not path or not os.path.exists(path): return redirect(url_for("index"))

        status["live_output"] = [f"--- Démarrage de {choice} ---"]
        log_to_db("SYSTEM", f"Démarrage manuel de {choice}")

        process = subprocess.Popen(["python3", path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        threading.Thread(target=read_output, args=(process, choice), daemon=True).start()
        threading.Thread(target=monitor_inactivity, args=(process, choice), daemon=True).start()

        status["running"] = True
        status["script_name"] = choice
        status["process"] = process
        status["last_activity"] = datetime.now()

    return redirect(url_for("index"))

@app.route("/stop", methods=["POST"])
def stop_script():
    if status["running"] and status["process"]:
        try:
            os.kill(status["process"].pid, signal.SIGTERM)
            log_to_db("SYSTEM", f"Arrêt manuel de {status['script_name']}")
            status["live_output"].append("--- Script arrêté manuellement ---")
        except Exception as e:
            log_to_db("SYSTEM", f"Erreur arrêt: {e}")
        status["running"] = False
        status["script_name"] = None
        status["process"] = None
    return redirect(url_for("index"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session['logged_in'] = True
            session['user'] = user
            return redirect(url_for('settings'))
        else:
            error = 'Identifiant ou mot de passe incorrect.'
    return render_template_string(LOGIN_HTML, error=error, glass_css=GLASS_CSS)

@app.route('/settings')
def settings():
    if not session.get('logged_in'): return redirect(url_for('login'))
    current_lock = get_setting('lock_launch')
    return render_template_string(SETTINGS_HTML, locked=current_lock, glass_css=GLASS_CSS)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if not session.get('logged_in'): return redirect(url_for('login'))
    lock_val = request.form.get('lock_launch', '0')
    set_setting('lock_launch', lock_val)
    flash("Paramètres mis à jour.")
    return redirect(url_for('settings'))

@app.route('/cleanup_logs', methods=['POST'])
def cleanup_logs():
    if not session.get('logged_in'): return redirect(url_for('login'))
    try:
        days = int(request.form.get('days', 50))
        limit_date = datetime.now() - timedelta(days=days)
        limit_str = limit_date.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM logs WHERE date < ?", (limit_str,))
        count = c.rowcount
        conn.commit()
        conn.close()
        flash(f"Succès : {count} logs supprimés.")
    except Exception as e:
        flash(f"Erreur : {e}")
    return redirect(url_for('settings'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
