from flask import Flask, request, jsonify
from flask_cors import CORS

import requests
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)


PEAK_FILE = 'peak_ccu.json'  # Persistent storage

def load_peak():
    if os.path.exists(PEAK_FILE):
        with open(PEAK_FILE, 'r') as f:
            data = json.load(f)
            return data.get('peak'), data.get('date')
    return 0, None

def save_peak(peak, date_str):
    with open(PEAK_FILE, 'w') as f:
        json.dump({'peak': peak, 'date': date_str}, f)

@app.route('/get_game')
def handle_game():
    id_ = request.args.get('id') 
    url = f'https://games.roblox.com/v1/games?universeIds={id_}'
    data = requests.get(url)

    if data.status_code != 200:
        return 500

    response = data.json()

    playing = response['data'][0].get('playing')
    visits = response['data'][0].get('visits')

    return jsonify({"playing": format_number(playing), "visits": format_number(visits)})


@app.route('/peak_ccu', methods=['GET', 'POST'])
def peak_ccu():
    universe_str = request.args.get('universes', '')
    if not universe_str:
        return jsonify({'error': 'No universes provided'}), 400
    
    universes = [int(id.strip()) for id in universe_str.split(',') if id.strip().isdigit()]
    if not universes:
        return jsonify({'error': 'Invalid universes'}), 400
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    current_peak, peak_date = load_peak()
    
    if peak_date != today:
        current_peak = 0
        peak_date = today
    
    # Batch fetch (split if >100)
    current_ccu = 0
    batch_size = 100
    for i in range(0, len(universes), batch_size):
        batch = universes[i:i+batch_size]
        ids_str = ','.join(map(str, batch))
        url = f'https://games.roblox.com/v1/games?universeIds={ids_str}'
        try:
            resp = requests.get(url).json()
            for game in resp.get('data', []):
                current_ccu += game.get('playing', 0)
        except Exception:
            pass  # Handle API errors gracefully
    
    if current_ccu > current_peak:
        current_peak = current_ccu
        save_peak(current_peak, peak_date)
    
    return jsonify({
        'current_ccu': current_ccu,
        'peak_ccu': current_peak,
        'date': peak_date,
        'is_new_day': peak_date != today 
    })


def format_number(num):
    if num >= 1_000_000_000:
        return f'{num/1_000_000_000:.2f}B'
    elif num >= 1_000_000:
        return f'{num/1_000_000:.1f}M'
    elif num >= 1_000:
        return f'{num/1_000:.2f}K'
    else:
        return str(int(num))
    

if __name__ == '__main__':
    app.run(debug=True)
