from flask import Flask, request, jsonify, send_from_directory
from google import genai

app = Flask(__name__)
client = genai.Client(api_key="YOUR_KEY")

def get_data():
    # dummy for now, replace with a SQLite query later
    return {"income": 30000, "spent_today": 640, "daily_budget": 1000,
            "week": {"Food": 2100, "Travel": 900, "Other": 600}}

@app.post("/api/chat")
def chat():
    q = request.json["message"]
    d = get_data()
    prompt = f"""You are PaisaFlow, a calm and friendly money assistant. Answer briefly in simple words, using ₹.
        User data: monthly income ₹{d['income']}, spent today ₹{d['spent_today']} of ₹{d['daily_budget']} daily budget,
        this week's spending: {d['week']}.
        Question: {q}"""
    res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return jsonify(reply=res.text)

@app.get("/")
def home():
    return send_from_directory(".", "paisaflow-chat.html")

app.run(debug=True)