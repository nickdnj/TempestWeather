# requirements: flask, pillow
from flask import Flask, send_file
import io
import json
import os
from tempest_overlay_image import create_tempest_overlay

app = Flask(__name__)

# Path to the latest Tempest JSON data (update as needed)
DATA_PATH = os.getenv('TEMPEST_JSON_PATH', '/tmp/tempest_latest.json')

@app.route('/overlay')
def overlay():
    # Try to load the latest data from file, fallback to example
    try:
        with open(DATA_PATH, 'r') as f:
            data = json.load(f)
    except Exception:
        data = {
            "primary_condition": "clear",
            "icon": "clear.png",
            "humidity": 55.02,
            "wind_speed": 10,
            "wind_direction": "W",
            "feels_like": 93.2,
            "units": "imperial"
        }
    img_bytes = create_tempest_overlay(data)
    return send_file(img_bytes, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050) 