# Permet de contrôler BotJanus à distance d'une console grâce à un site Flask
from flask import Flask, render_template_string, redirect, url_for, request
import subprocess
import os
import signal
import threading

app = Flask(__name__)

# --- état du bot ---
status = {
    "running": False,
    "process": None,
    "script_name": None,
    "output": []
}

# --- scripts et chemins ---
# Scripts personnels à retrouver dans la repo GitHub mais il faudra changer pour vous le chemin d'accès !
SCRIPTS = {
    "Uncategorized": "/home/Janus/bots/uncategorized.py",
    "Orphan": "/home/Janus/bots/orphan.py",
    "Interwiki-EN": "/home/Janus/bots/interwiki-en.py"
}

# --- fonction pour lire la sortie du script ---
def read_output(process):
    for line in iter(process.stdout.readline, ''):
        status["output"].append(line.strip())
    process.stdout.close()

# --- HTML du dashboard (modifié uniquement côté affichage) ---
HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>BotJanus - Dashboard</title>
  <style>
    body { font-family: sans-serif; text-align:center; margin-top:20px; }
    button { padding: 10px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; border:none; margin:5px; }
    .run { background: #4CAF50; color: white; }
    .stop { background: #f44336; color: white; }
    .accordion { background-color: #eee; cursor: pointer; padding: 10px; width: 80%; margin: auto; border-radius: 8px; text-align:left; border:none; outline:none; transition: 0.4s; }
    .panel { padding: 0 10px; display: none; background-color: white; width: 80%; margin: auto; overflow: hidden; border: 1px solid #ccc; border-radius: 8px; text-align:left; }
    pre { white-space: pre-wrap; word-wrap: break-word; }
  </style>
</head>
<body>
  <h1>BotJanus - Dashboard</h1>

  <div>État : <b>{{ 'En cours (' + script_name + ')' if running else 'Arrêté' }}</b></div>

  <form onsubmit="startScript(); return false;">
    <button class="run" type="submit">Démarrer un script</button>
  </form>
  <form action="{{ url_for('stop_script') }}" method="post">
    <button class="stop" type="submit">Arrêter le script</button>
  </form>

  <button class="accordion">Voir les logs du script</button>
  <div class="panel"><pre>{{ logs }}</pre></div>

  <script>
    function startScript() {
      let choice = prompt(
        "Quel script veux-tu lancer ?\\n" +
        "1 - Uncategorized\\n" +
        "2 - Orphan\\n" +
        "3 - Interwiki-EN"
      );
      if (!choice) return;

      let map = { "1":"Uncategorized", "2":"Orphan", "3":"Interwiki-EN" };
      let selected = map[choice];
      if (!selected) return;

      let form = document.createElement("form");
      form.method = "POST"; form.action = "/start";
      let input = document.createElement("input"); input.type="hidden"; input.name="choice"; input.value=selected;
      form.appendChild(input); document.body.appendChild(form); form.submit();
    }

    var acc = document.getElementsByClassName("accordion");
    for (var i=0; i<acc.length; i++){
      acc[i].addEventListener("click", function(){
        this.classList.toggle("active");
        var panel = this.nextElementSibling;
        panel.style.display = (panel.style.display === "block") ? "none" : "block";
      });
    }

    setInterval(function(){
      fetch("/logs")
        .then(r=>r.text())
        .then(data => { document.querySelector(".panel pre").innerText = data; });
    }, 5000);
  </script>
</body>
</html>
"""

# --- routes Flask ---
@app.route("/")
def index():
    return render_template_string(
        HTML,
        running=status["running"],
        script_name=status.get("script_name") or "aucun",
        logs="\n".join(status["output"][-50:])
    )

@app.route("/start", methods=["POST"])
def start_script():
    if not status["running"]:
        choice = request.form.get("choice")
        path = SCRIPTS.get(choice)
        if not path or not os.path.exists(path):
            print(f"[ERREUR] Le chemin {path} n'existe pas !", flush=True)
            return redirect(url_for("index"))

        print(f"[INFO] Lancement du script : {path}", flush=True)
        process = subprocess.Popen(
            ["python3", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        threading.Thread(target=read_output, args=(process,), daemon=True).start()
        status["running"] = True
        status["script_name"] = choice
        status["process"] = process
    return redirect(url_for("index"))

@app.route("/stop", methods=["POST"])
def stop_script():
    if status["running"] and status["process"]:
        try: os.kill(status["process"].pid, signal.SIGTERM)
        except Exception as e: print(f"[ERREUR] Impossible de tuer le script: {e}", flush=True)
        status["running"] = False
        status["script_name"] = None
        status["process"] = None
    return redirect(url_for("index"))

@app.route("/logs")
def logs():
    return "\n".join(status["output"][-100:])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
