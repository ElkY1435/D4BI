from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os

app = Flask(__name__)
CORS(app, origins="*")

# La API key viene de variable de entorno (más seguro)
ANT_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

@app.route('/')
def home():
    return jsonify({"status": "D4BI Server corriendo", "version": "1.0"})

@app.route('/health')
def health():
    return jsonify({"ok": True})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        if not ANT_KEY:
            return jsonify({"error": "API key no configurada"}), 500

        data = request.json
        client = anthropic.Anthropic(api_key=ANT_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=data.get('system', ''),
            messages=data.get('messages', [])
        )
        return jsonify({"content": [{"text": message.content[0].text}]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3001))
    print(f"D4BI Server corriendo en puerto {port}")
    app.run(host='0.0.0.0', port=port)
