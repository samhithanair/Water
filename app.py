from flask import Flask, render_template, request, jsonify, session
import uuid
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
from datetime import date

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or "super-secret-key"  # Required for session

RESPONSES_DIR = "responses"
PROMPT_FILE = "daily_prompt.json"


os.makedirs(RESPONSES_DIR, exist_ok=True)

def get_today():
    return date.today().isoformat()

def get_today_prompt():
    today = get_today()

    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r") as f:
            data = json.load(f)
            if data.get("date") == today:
                return data["prompt"]

    model = genai.GenerativeModel('models/gemini-1.5-pro-001')
    response = model.generate_content(
        """You are an empathetic agent, designed to ask thought-provoking questions. 
        Generate one question and avoid cliches. Always generate a different prompt to the user. 
        You want to give an open ended question and be nice. """
    )
    prompt = response.text.strip()

    with open(PROMPT_FILE, "w") as f:
        json.dump({"date": today, "prompt": prompt}, f)

    return prompt

def get_user_response_path():
    user_id = session.get("user_id")
    user_dir = os.path.join(RESPONSES_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, f"{get_today()}.json")

def get_today_response():
    filename = get_user_response_path()
    if os.path.exists(filename):
        with open(filename, "r") as f:
            data = json.load(f)
            return data.get("response", "")

def save_today_response(text):
    filename = get_user_response_path()
    prompt = get_today_prompt()
    with open(filename, "w") as f:
        json.dump({"prompt": prompt, "response": text.strip()}, f, indent=2)

@app.before_request
def assign_user_id():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())


@app.route('/')
def index():
    prompt = get_today_prompt()
    response = get_today_response()
    return render_template("index.html", prompt=prompt, response=response)

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json
    answer = data.get("answer", "").strip()

    if answer:
        save_today_response(answer)
        return jsonify({"success": True, "message": "Response saved."})
    return jsonify({"success": False, "message": "No response submitted."})

@app.route('/history')
def history():
    user_id = session.get("user_id")
    user_dir = os.path.join(RESPONSES_DIR, user_id)
    entries = []

    if os.path.exists(user_dir):
        for filename in sorted(os.listdir(user_dir)):
            if filename.endswith(".json"):
                date_str = filename.replace(".json", "")
                with open(os.path.join(user_dir, filename), "r") as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, dict) and "response" in data:
                            entries.append({
                                "date": date_str,
                                "prompt": data.get("prompt", "[No prompt found]"),
                                "response": data["response"]
                            })
                    except Exception:
                        continue
    entries.reverse()
    return render_template("history.html", entries=entries)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
