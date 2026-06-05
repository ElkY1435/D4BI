from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import requests
import os

app = Flask(__name__)
CORS(app, origins="*")

ANT_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CG_KEY  = os.environ.get("CG_KEY", "CG-7dMPaBGUibViZMDVuBFFeUsN")

@app.route('/')
def home():
    return jsonify({"status": "D4BI Server corriendo", "version": "2.0"})

@app.route('/health')
def health():
    return jsonify({"ok": True})

# ===== PROXY CRYPTO (CoinGecko) =====
@app.route('/crypto/prices', methods=['GET'])
def crypto_prices():
    try:
        ids = 'bitcoin,ethereum,solana,binancecoin,ripple'
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true&precision=2&x_cg_demo_api_key={CG_KEY}'
        res = requests.get(url, timeout=10)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/crypto/history/<symbol>', methods=['GET'])
def crypto_history(symbol):
    try:
        days = request.args.get('days', 30)
        cg_map = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
            'BNB': 'binancecoin', 'XRP': 'ripple'
        }
        cg_id = cg_map.get(symbol.upper())
        if not cg_id:
            return jsonify({"error": "Symbol not found"}), 404
        url = f'https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart?vs_currency=usd&days={days}&interval=daily&x_cg_demo_api_key={CG_KEY}'
        res = requests.get(url, timeout=10)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== PROXY STOCKS (Yahoo Finance) =====
@app.route('/stocks/prices', methods=['GET'])
def stock_prices():
    try:
        symbols = 'MSFT,AAPL,GOOGL,AMZN,META,ORCL,CRM,SAP,MELI,YPF,%5EGSPC'
        url = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}&fields=regularMarketPrice,regularMarketChangePercent'
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
        res = requests.get(url, headers=headers, timeout=10)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stocks/history/<symbol>', methods=['GET'])
def stock_history(symbol):
    try:
        days  = int(request.args.get('days', 30))
        import time
        period2 = int(time.time())
        period1 = period2 - (days * 86400)
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={period1}&period2={period2}&interval=1d'
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
        res = requests.get(url, headers=headers, timeout=10)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== CHAT IA =====
@app.route('/chat', methods=['POST'])
def chat():
    try:
        if not ANT_KEY:
            return jsonify({"error": "API key no configurada"}), 500
        data   = request.json
        client = anthropic.Anthropic(api_key=ANT_KEY)
        msg    = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=data.get('system', ''),
            messages=data.get('messages', [])
        )
        return jsonify({"content": [{"text": msg.content[0].text}]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3001))
    print(f"D4BI Server v2.0 corriendo en puerto {port}")
    app.run(host='0.0.0.0', port=port)
