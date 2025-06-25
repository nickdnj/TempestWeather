import os
import io
from PIL import Image, ImageDraw, ImageFont

# Paths
FONT_PATH = os.path.join(os.path.dirname(__file__), '../fonts/Arial.ttf')
ICONS_PATH = os.path.join(os.path.dirname(__file__), '../weather_icons')

# Helper to load icon
def load_icon(icon_name, size):
    path = os.path.join(ICONS_PATH, icon_name)
    icon = Image.open(path).convert('RGBA')
    if size:
        icon = icon.resize(size, Image.ANTIALIAS)
    return icon

def create_tempest_overlay(data, output_path=None):
    # Extract data
    icon_file = data.get('icon', 'unknown.png')
    feels_like = data.get('feels_like', '--')
    humidity = data.get('humidity', '--')
    wind_speed = data.get('wind_speed', '--')
    wind_direction = data.get('wind_direction', '--')

    # Sizing
    icon_size = (90, 90)
    small_icon_size = (40, 40)
    padding = 24
    spacing = 32
    bg_radius = 32
    bg_alpha = 180  # 0-255
    font_big = 64
    font_small = 36
    font = ImageFont.truetype(FONT_PATH, font_big)
    font_small_obj = ImageFont.truetype(FONT_PATH, font_small)

    # Prepare icons
    weather_icon = load_icon(icon_file, icon_size)
    humidity_icon = load_icon('humidity.png', small_icon_size)
    wind_icon = load_icon('wind.png', small_icon_size)

    # Prepare text
    temp_text = f"{feels_like:.0f}" if isinstance(feels_like, (int, float)) else str(feels_like)
    humidity_text = f"{humidity:.0f}" if isinstance(humidity, (int, float)) else str(humidity)
    wind_text = f"{wind_speed:.0f}" if isinstance(wind_speed, (int, float)) else str(wind_speed)
    wind_dir_text = str(wind_direction)

    # Measure text
    temp_size = font.getsize(temp_text)
    humidity_size = font_small_obj.getsize(humidity_text)
    wind_size = font_small_obj.getsize(wind_text)
    wind_dir_size = font_small_obj.getsize(wind_dir_text)

    # Calculate total width
    width = (
        padding * 2 +
        icon_size[0] + spacing +
        temp_size[0] + spacing +
        small_icon_size[0] + humidity_size[0] + spacing +
        small_icon_size[0] + wind_size[0] + wind_dir_size[0]
    )
    height = max(icon_size[1], temp_size[1], small_icon_size[1] + humidity_size[1], small_icon_size[1] + wind_size[1]) + padding * 2

    # Create background
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Semi-transparent rounded rectangle
    draw.rounded_rectangle([(0, 0), (width, height)], radius=bg_radius, fill=(0, 0, 0, bg_alpha))

    # Paste elements
    x = padding
    y = (height - icon_size[1]) // 2
    overlay.paste(weather_icon, (x, y), weather_icon)
    x += icon_size[0] + spacing

    y = (height - temp_size[1]) // 2
    draw.text((x, y), temp_text, font=font, fill='white')
    x += temp_size[0] + spacing

    y = (height - small_icon_size[1]) // 2
    overlay.paste(humidity_icon, (x, y), humidity_icon)
    x += small_icon_size[0]
    y = (height - humidity_size[1]) // 2
    draw.text((x, y), humidity_text, font=font_small_obj, fill='white')
    x += humidity_size[0] + spacing

    y = (height - small_icon_size[1]) // 2
    overlay.paste(wind_icon, (x, y), wind_icon)
    x += small_icon_size[0]
    y = (height - wind_size[1]) // 2
    draw.text((x, y), wind_text, font=font_small_obj, fill='white')
    x += wind_size[0]
    y = (height - wind_dir_size[1]) // 2
    draw.text((x, y), wind_dir_text, font=font_small_obj, fill='white')

    # Save or return
    if output_path:
        overlay.save(output_path, 'PNG')
        return output_path
    else:
        img_byte_arr = io.BytesIO()
        overlay.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr

# Example usage:
if __name__ == "__main__":
    # Example JSON
    data = {
        "primary_condition": "clear",
        "icon": "clear.png",
        "humidity": 55.02,
        "wind_speed": 7.2,
        "wind_direction": "W",
        "feels_like": 93.2,
        "units": "imperial"
    }
    out = create_tempest_overlay(data, output_path="tempest_overlay_example.png")
    print(f"Overlay image saved to {out}") 