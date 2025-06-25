import socket
import json
import time

UDP_PORT = 50222

# Mapping for precipitation_type
PRECIP_TYPE_MAP = {
    0: 'none',
    1: 'rain',
    2: 'hail',
    3: 'rain_hail'
}

# Wind direction to compass
COMPASS_SECTORS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
]

def degrees_to_compass(degrees):
    if degrees is None:
        return "N"
    idx = int((degrees + 11.25) / 22.5) % 16
    return COMPASS_SECTORS[idx]

# Icon selection logic (simplified, can be expanded)
def select_icon(primary_condition):
    icon_map = {
        'rain': 'rain.png',
        'hail': 'hail.png',
        'rain_hail': 'rain.png',
        'windy': 'wind.png',
        'clear': 'clear.png',
        'cloudy': 'clouds.png',
        'none': 'clear.png',
    }
    return icon_map.get(primary_condition, 'unknown.png')

def determine_primary_condition(obs):
    # obs indices per Tempest UDP API
    precipitation_type = obs[13]
    wind_avg = obs[2]
    solar_radiation = obs[11]
    uv = obs[10]
    humidity = obs[8]
    # Precipitation takes precedence
    if precipitation_type == 1:
        return 'rain'
    elif precipitation_type == 2:
        return 'hail'
    elif precipitation_type == 3:
        return 'rain_hail'
    # Windy if wind_avg > 8 m/s (~18 mph)
    elif wind_avg is not None and wind_avg > 8:
        return 'windy'
    # Clear if solar_radiation or uv is high
    elif solar_radiation is not None and solar_radiation > 500:
        return 'clear'
    elif uv is not None and uv > 5:
        return 'clear'
    # Cloudy if humidity is high and solar is low
    elif humidity is not None and humidity > 80 and (solar_radiation is None or solar_radiation < 200):
        return 'cloudy'
    else:
        return 'none'

# Conversion helpers
def ms_to_mph(ms):
    return round(ms * 2.23694, 1) if ms is not None else None

def c_to_f(c):
    return round(c * 9/5 + 32, 1) if c is not None else None

def get_current_conditions():
    """
    Listen for Tempest UDP packets and return the latest current conditions as a dict.
    Waits indefinitely until an obs_st packet is received.
    All output values are in English (Imperial) units.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", UDP_PORT))
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            msg = json.loads(data.decode())
            if msg.get("type") == "obs_st" and "obs" in msg and msg["obs"]:
                obs = msg["obs"][0]
                # Extract fields
                humidity = obs[8]  # %
                wind_speed_ms = obs[2]  # m/s
                wind_speed = ms_to_mph(wind_speed_ms)  # mph
                wind_direction_deg = obs[4]
                wind_direction = degrees_to_compass(wind_direction_deg)
                feels_like_c = obs[21] if len(obs) > 21 and obs[21] is not None else obs[7]
                feels_like = c_to_f(feels_like_c)  # F
                primary_condition = determine_primary_condition(obs)
                icon = select_icon(primary_condition)
                result = {
                    "primary_condition": primary_condition,
                    "icon": icon,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "wind_direction": wind_direction,
                    "feels_like": feels_like,
                    "units": "imperial"
                }
                sock.close()
                return result
        except Exception:
            continue

if __name__ == "__main__":
    result = get_current_conditions()
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("No Tempest UDP data received. Make sure your device is on the same network and broadcasting.") 