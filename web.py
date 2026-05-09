from flask import Flask, render_template_string
import json
import os

app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

@app.route("/")
def home():
    data = load_data()

    html = """
    <h1>📊 لوحة الطلبات</h1>
    <h3>عدد الطلبات: {{count}}</h3>
    <hr>
    {% for d in data %}
        <p><b>{{d['name']}}</b>: {{d['message']}}</p>
        <hr>
    {% endfor %}
    """

    return render_template_string(html, data=data, count=len(data))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
