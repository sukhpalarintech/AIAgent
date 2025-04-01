from flask import Flask, request, jsonify
from flask_cors import CORS
from chatbot import chatbot

app = Flask(__name__)
CORS(app, supports_credentials=True)  # ✅ Allow OPTIONS requests

@app.route("/chat", methods=["OPTIONS", "POST"])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"message": "CORS Preflight OK"}), 200  # ✅ Respond to OPTIONS

    data = request.get_json()
    if not data or "message" not in data or "user_email" not in data:
        return jsonify({"error": "Missing 'message' or 'user_email'"}), 400

    message = data["message"]
    user_email = data["user_email"]
    return jsonify(chatbot(message, user_email))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
