# requirements: flask, pillow
from flask import Flask, send_file, request
from io import BytesIO
from seaer_cwt_overlay import seaer_cwt_overlay

app = Flask(__name__)

@app.route('/overlay')
def overlay():
    # Get parameters from query string or use defaults
    location1 = request.args.get('location1', 'Shrewsberry River')
    location2 = request.args.get('location2', 'Monmouth Beach NJ')
    stationName = request.args.get('stationName', '8531942')

    # Generate overlay image (should return BytesIO or file path)
    overlay_image = seaer_cwt_overlay(location1, location2, stationName)

    # If the overlay_image is a file path, open it as BytesIO
    if not isinstance(overlay_image, BytesIO):
        with open(overlay_image, 'rb') as f:
            overlay_image = BytesIO(f.read())
    overlay_image.seek(0)
    return send_file(overlay_image, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 