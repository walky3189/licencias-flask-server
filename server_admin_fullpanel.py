from flask import Flask, request, redirect, render_template_string, send_file
import sqlite3
from datetime import datetime, timedelta
import csv
import io
import os

app = Flask(__name__)
DB_PATH = "licenses.db"

HTML_PANEL = """<h2>🔐 Panel de Licencias</h2>
<p><a href="/">🔄 Actualizar</a> | <a href="/logs">📜 Ver logs</a> | <a href="/export">📁 Exportar CSV</a> | <a href="/usos">📊 Usos</a></p>

<h3>➕ Crear nueva licencia</h3>
<form method="post" action="/add">
    Clave: <input name="key" required>
    HWID (opcional): <input name="hwid">
    Expira en:
    <select name="duracion">
        <option value="1">1 día</option>
        <option value="7">1 semana</option>
        <option value="30">1 mes</option>
        <option value="infinito">Infinito</option>
    </select>
    <button type="submit">Crear</button>
</form>

<h3>🔍 Buscar licencia</h3>
<form method="get" action="/">
    <input name="buscar" placeholder="Clave o HWID">
    <button type="submit">Buscar</button>
</form>

<h3>📋 Lista de licencias</h3>
<table border=1 cellpadding=6>
<tr><th>Clave</th><th>HWID</th><th>Expira</th><th>Estado</th><th>Acción</th></tr>
{% for lic in licencias %}
<tr>
  <td>{{ lic[0] }}</td>
  <td>{{ lic[1] or "⚠️ No asignado" }}</td>
  <td>{{ lic[2] }}</td>
  <td>
    {% if lic[2] < hoy %}
        ❌ Expirada
    {% elif lic[1] %}
        ✅ Activa
    {% else %}
        ⏳ Pendiente
    {% endif %}
  </td>
  <td><a href="/delete/{{ lic[0] }}">❌ Eliminar</a></td>
</tr>
{% endfor %}
</table>"""

@app.route("/")
def index():
    buscar = request.args.get("buscar", "")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if buscar:
        cursor.execute("SELECT key, hwid, expires FROM licenses WHERE key LIKE ? OR hwid LIKE ?", 
                       (f"%{buscar}%", f"%{buscar}%"))
    else:
        cursor.execute("SELECT key, hwid, expires FROM licenses ORDER BY expires")
    licencias = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_PANEL, licencias=licencias, hoy=datetime.now().strftime("%Y-%m-%d"))

@app.route("/add", methods=["POST"])
def add():
    key = request.form["key"]
    hwid = request.form["hwid"]
    duracion = request.form["duracion"]
    expires = "2099-12-31" if duracion == "infinito" else (datetime.now() + timedelta(days=int(duracion))).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO licenses (key, hwid, expires) VALUES (?, ?, ?)", 
                   (key, hwid if hwid else None, expires))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<key>")
def delete(key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM licenses WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/logs")
def logs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY fecha DESC")
    logs = cursor.fetchall()
    conn.close()
    return render_template_string("<h2>📜 Registros</h2><p><a href='/'>⬅️ Volver</a></p><table border=1><tr><th>ID</th><th>Clave</th><th>HWID</th><th>Fecha</th><th>Estado</th></tr>{% for log in logs %}<tr><td>{{ log[0] }}</td><td>{{ log[1] }}</td><td>{{ log[2] }}</td><td>{{ log[3] }}</td><td>{{ log[4] }}</td></tr>{% endfor %}</table>", logs=logs)

@app.route("/export")
def export():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, hwid, expires FROM licenses")
    rows = cursor.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Key", "HWID", "Expires"])
    writer.writerows(rows)
    output.seek(0)
    conn.close()
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="licencias.csv")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))