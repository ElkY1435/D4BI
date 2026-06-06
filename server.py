from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import requests
import os
import time

app = Flask(__name__)
CORS(app, origins="*")

ANT_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
CG_KEY   = os.environ.get("CG_KEY", "CG-7dMPaBGUibViZMDVuBFFeUsN")
AV_KEY   = os.environ.get("AV_KEY", "BRPUJDC06V2HC2M9")

@app.route('/')
def home():
    return jsonify({"status": "D4BI Server v3.0", "ok": True})

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

# ===== PROXY STOCKS (Alpha Vantage) =====
# Cache para no gastar llamadas (25/día límite)
stock_cache = {}
stock_cache_time = {}
CACHE_TTL = 900  # 15 minutos

TICKERS = ['MSFT','AAPL','GOOGL','AMZN','META','ORCL','CRM','SAP','MELI','YPF','SPY']

def get_stock_quote(symbol):
    now = time.time()
    if symbol in stock_cache and (now - stock_cache_time.get(symbol, 0)) < CACHE_TTL:
        return stock_cache[symbol]
    try:
        url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={AV_KEY}'
        res = requests.get(url, timeout=10)
        data = res.json()
        q = data.get('Global Quote', {})
        if not q or '05. price' not in q:
            return None
        result = {
            'symbol': symbol,
            'price': float(q.get('05. price', 0)),
            'change_pct': float(q.get('10. change percent', '0%').replace('%',''))
        }
        stock_cache[symbol] = result
        stock_cache_time[symbol] = now
        return result
    except:
        return None

@app.route('/stocks/prices', methods=['GET'])
def stock_prices():
    try:
        # Alpha Vantage no permite batch, usamos cache agresivo
        results = []
        for sym in TICKERS:
            cached = stock_cache.get(sym)
            if cached:
                results.append(cached)

        # Si el cache está vacío, traemos los primeros 5 (límite de burst)
        if not results:
            for sym in TICKERS[:5]:
                q = get_stock_quote(sym)
                if q:
                    results.append(q)
                time.sleep(0.5)

        return jsonify({"quotes": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stocks/refresh', methods=['GET'])
def stocks_refresh():
    """Actualiza un símbolo específico del cache"""
    try:
        symbol = request.args.get('symbol', '').upper()
        if symbol not in TICKERS:
            return jsonify({"error": "Symbol not supported"}), 400
        result = get_stock_quote(symbol)
        if result:
            return jsonify(result)
        return jsonify({"error": "No data"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stocks/history/<symbol>', methods=['GET'])
def stock_history(symbol):
    try:
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={AV_KEY}'
        res = requests.get(url, timeout=15)
        data = res.json()
        ts = data.get('Time Series (Daily)', {})
        if not ts:
            return jsonify({"error": "No data"}), 404
        days = int(request.args.get('days', 30))
        items = sorted(ts.items())[-days:]
        result = [{'date': d, 'price': float(v['4. close'])} for d, v in items]
        return jsonify(result)
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
    print(f"D4BI Server v3.0 corriendo en puerto {port}")
    app.run(host='0.0.0.0', port=port)
