from PIL import Image, ImageDraw, ImageFont
import io
from seaer_ai.get_next_tide_event import get_next_tide_event
from seaer_ai.get_current_nws_weather import get_nws_current_observations_data

def create_text_image(text, size, pointsize, font_path, padding=(0, 0)):
    width, height = size
    padded_size = (width + 2 * padding[0], height + 2 * padding[1])
    image = Image.new('RGBA', padded_size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, pointsize)
    draw.text((padding[0], padding[1]), text, fill="white", font=font)
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def image_from_bytes(img_byte_arr):
    img_byte_arr.seek(0)
    return Image.open(img_byte_arr)

def seaer_cwt_overlay(location1, location2, stationName):
    # Add logic here to derive values for weather_icon_path, tide_icon_path, font_path, temp, wind_dir, wind_speed, tide_hl, tide_time, temp_max, temp_min
    # Example:
    # Get Tide Data
    tide_event_data = get_next_tide_event(stationName)
    tide_hl = tide_event_data.get('event_type', "Station")
    tide_time = tide_event_data.get('event_time', 'Error')
    tide_icon_path = tide_event_data.get('tide_icon',"./weather_icons/low_tide.png")   

    
    # Get Current Weather Data
    # Getting and saving nws Present Weather
    weather_location = location2
    present_weather_data = get_nws_current_observations_data(weather_location)
    #print("present_weather_data", present_weather_data)
    textDescription = present_weather_data.get('textDescription', 'unknown')
    weather_raw_string = present_weather_data.get('weather_rawString', 'unknown')  
    temperature = present_weather_data.get('temperature', 'unknown')
    dewpoint = present_weather_data.get('dewpoint', 'unknown')
    wind_dir = present_weather_data.get('windDirection', 'unknown')
    wind_speed = present_weather_data.get('windSpeed', 'unknown')  
    wind_gust = present_weather_data.get('windGust', 'unknown')
    barometric_pressure = present_weather_data.get('barometricPressure', 'unknown')
    sea_level_pressure = present_weather_data.get('seaLevelPressure', 'unknown')
    visibility = present_weather_data.get('visibility', 'unknown')
    relative_humidity = present_weather_data.get('relativeHumidity', 'unknown')
    wind_chill = present_weather_data.get('windChill', 'unknown')
    heat_index = present_weather_data.get('heatIndex', 'unknown')

    #wind_degrees = weather_data['wind_degrees']
    #wind_speed = weather_data['wind_speed']
    #wind_dir = weather_data['wind_dir']
    #current_conditions = weather_data['current_conditions'] 
    #NICK NEED to fix this weather icons path
    #weather_icon_path = "./weather_icons/unknown.png"   
    # Defining the mapping based on the provided text descriptions and corresponding icons.
    weather_icons = {
        "A Few Clouds": "./weather_icons/clouds.png",
        "A Few Clouds and Breezy": "./weather_icons/clouds.png",
        "A Few Clouds and Windy": "./weather_icons/clouds.png",
        "A Few Clouds with Haze": "./weather_icons/clouds.png",
        "Blizzard": "./weather_icons/snow.png",
        "Blowing Dust": "./weather_icons/dust.png",
        "Blowing Sand": "./weather_icons/sand.png",
        "Blowing Snow": "./weather_icons/snow.png",
        "Blowing Snow in Vicinity": "./weather_icons/snow.png",
        "Breezy": "./weather_icons/wind.png",
        "Clear": "./weather_icons/clear.png",
        "Clear and Breezy": "./weather_icons/clear.png",
        "Clear with Haze": "./weather_icons/clear.png",
        "Cold": "./weather_icons/snow.png",
        "Drizzle": "./weather_icons/drizzle.png",
        "Drizzle Fog": "f./weather_icons/og.png",
        "Drizzle Fog/Mist": "./weather_icons/fog.png",
        "Drizzle Ice Pellets": "./weather_icons/snow.png",
        "Drizzle Snow": "./weather_icons/snow.png",
        "Dust": "./weather_icons/dust.png",
        "Dust Storm": "./weather_icons/dust.png",
        "Dust Storm in Vicinity": "./weather_icons/dust.png",
        "Dust/Sand Whirls": "./weather_icons/dust.png",
        "Dust/Sand Whirls in Vicinity": "./weather_icons/dust.png",
        "Fair": "./weather_icons/clear.png",
        "Fair and Breezy": "./weather_icons/clear.png",
        "Fair and Windy": "./weather_icons/clear.png",
        "Fair with Haze": "./weather_icons/clear.png",
        "Fog in Vicinity": "./weather_icons/fog.png",
        "Fog/Mist": "./weather_icons/fog.png",
        "Freezing Drizzle": "./weather_icons/drizzle.png",
        "Freezing Drizzle Rain": "./weather_icons/rain.png",
        "Freezing Drizzle Snow": "./weather_icons/snow.png",
        "Freezing Drizzle in Vicinity": "./weather_icons/drizzle.png",
        "Freezing Fog": "./weather_icons/fog.png",
        "Freezing Fog in Vicinity": "./weather_icons/fog.png",
        "Freezing Rain": "./weather_icons/rain.png",
        "Freezing Rain Rain": "./weather_icons/rain.png",
        "Freezing Rain Snow": "./weather_icons/snow.png",
        "Freezing Rain in Vicinity": "./weather_icons/rain.png",
        "Funnel Cloud": "./weather_icons/tornado.png",
        "Funnel Cloud in Vicinity": "./weather_icons/tornado.png",
        "Hail": "./weather_icons/rain.png",
        "Hail Showers": "./weather_icons/rain.png",
        "Haze": "./weather_icons/haze.png",
        "Heavy Blowing Snow": "./weather_icons/snow.png",
        "Heavy Drizzle": "./weather_icons/drizzle.png",
        "Heavy Drizzle Fog": "./weather_icons/fog.png",
        "Heavy Drizzle Fog/Mist": "./weather_icons/fog.png",
        "Heavy Drizzle Ice Pellets": "./weather_icons/snow.png",
        "Heavy Drizzle Snow": "./weather_icons/snow.png",
        "Heavy Dust Storm": "./weather_icons/dust.png",
        "Heavy Freezing Drizzle": "./weather_icons/drizzle.png",
        "Heavy Freezing Drizzle Rain": "./weather_icons/rain.png",
        "Heavy Freezing Drizzle Snow": "./weather_icons/snow.png",
        "Heavy Freezing Fog": "./weather_icons/fog.png",
        "Heavy Freezing Rain": "./weather_icons/rain.png",
        "Heavy Freezing Rain Rain": "./weather_icons/rain.png",
        "Heavy Freezing Rain Snow": "./weather_icons/snow.png",
        "Heavy Ice Pellets": "./weather_icons/snow.png",
        "Heavy Ice Pellets Drizzle": "./weather_icons/drizzle.png",
        "Heavy Ice Pellets Rain": "./weather_icons/rain.png",
        "Heavy Rain": "./weather_icons/rain.png",
        "Heavy Rain Fog": "./weather_icons/fog.png",
        "Heavy Rain Fog/Mist": "./weather_icons/fog.png",
        "Heavy Rain Freezing Drizzle": "./weather_icons/drizzle.png",
        "Heavy Rain Freezing Rain": "./weather_icons/rain.png",
        "Heavy Rain Ice Pellets": "./weather_icons/snow.png",
        "Heavy Rain Showers": "./weather_icons/rain.png",
        "Heavy Rain Showers Fog/Mist": "./weather_icons/fog.png",
        "Heavy Rain Snow": "./weather_icons/snow.png",
        "Heavy Sand Storm": "./weather_icons/sand.png",
        "Heavy Showers Rain": "./weather_icons/rain.png",
        "Heavy Showers Rain Fog/Mist": "./weather_icons/fog.png",
        "Heavy Showers Snow": "./weather_icons/snow.png",
        "Heavy Showers Snow Fog/Mist": "./weather_icons/fog.png",
        "Heavy Snow": "./weather_icons/snow.png",
        "Heavy Snow Blowing Snow": "./weather_icons/snow.png",
        "Heavy Snow Fog": "./weather_icons/fog.png",
        "Heavy Snow Fog/Mist": "./weather_icons/fog.png",
        "Heavy Snow Freezing Drizzle": "./weather_icons/drizzle.png",
        "Heavy Snow Freezing Rain": "./weather_icons/rain.png",
        "Heavy Snow Grains": "./weather_icons/snow.png",
        "Heavy Snow Low Drifting Snow": "./weather_icons/snow.png",
        "Heavy Snow Rain": "./weather_icons/rain.png",
        "Heavy Snow Showers": "./weather_icons/snow.png",
        "Heavy Snow Showers Fog": "./weather_icons/fog.png",
        "Heavy Snow Showers Fog/Mist": "./weather_icons/fog.png",
        "Heavy Thunderstorm Rain": "./weather_icons/thunderstorm.png",
        "Heavy Thunderstorm Rain Fog": "./weather_icons/fog.png",
        "Heavy Thunderstorm Rain Fog and Windy": "./weather_icons/thunderstorm.png",
        "Heavy Thunderstorm Rain Fog/Mist": "./weather_icons/fog.png",
        "Heavy Thunderstorm Rain Hail": "./weather_icons/thunderstorm.png",
        "Heavy Thunderstorm Rain Hail Fog": "./weather_icons/fog.png",
        "Heavy Thunderstorm Rain Hail Fog/Hail": "./weather_icons/thunderstorm.png",
        "Heavy Thunderstorm Rain Hail Haze": "./weather_icons/thunderstorm.png",
        "Heavy Thunderstorm Rain Haze": "./weather_icons/thunderstorm.png",
        "Heavy Thunderstorm Rain Sm": "./weather_icons/thunderstorm.png",
        # Mapping continues for each weather condition...
}

    weather_icon_path = weather_icons.get(textDescription, "./weather_icons/unknown.png")
    #print("textDescription", textDescription)
    #print("weather_icon_path", weather_icon_path)
    
    # #weather_icon_path = "./weather_icons/clear.png"
    # temp = "40°F"
    # wind_dir = "NNE"
    # wind_speed = "20 mph"
    
    # temp_max = "H 30°"
    # temp_min = "L 30°"
    # Constants
    wind_icon_path = "./weather_icons/wind.png"
    font_path = "/app/fonts/Arial.ttf"
    padding=1
    line_text = "_" * 700  # Line of underscores
    padding_tuple = (padding, padding)  # Padding for all images

    # Create Header PNG with padding
    loc1_img = create_text_image(location1, (1000, 50), 44, font_path)
    loc2_img = create_text_image(location2, (1000, 60), 54, font_path)
    line_img = create_text_image(line_text, (1000, 50), 25, font_path, (0,-20 ))

    # Create and assemble header
    header_parts = [image_from_bytes(loc1_img), image_from_bytes(loc2_img), image_from_bytes(line_img)]
    header_height = sum(p.size[1] for p in header_parts)
    header = Image.new('RGBA', (1000, header_height), (255, 255, 255, 0))
    y_offset = 0
    for part in header_parts:
        header.paste(part, (0, y_offset))
        y_offset += part.size[1]

    # Create Temperature PNG
    temp_img = create_text_image(temperature, (150, 100), 65, font_path, (10,0))
    
    # Create Temperature PNG
    humidity_img = create_text_image(relative_humidity, (150, 100), 65, font_path, (10,0))
    # # Create Temperature High/Low PNG
    # temp_max_img = create_text_image(temp_max, (160, 50), 40, font_path, (0,80))
    # temp_min_img = create_text_image(temp_min, (160, 50), 40, font_path, (0,0))

    # # Assemble Temperature High/Low with padding
    # temp_hl_parts = [image_from_bytes(temp_max_img), image_from_bytes(temp_min_img)]
    # temphl_height = sum(p.size[1] for p in temp_hl_parts) + padding * 2
    # temphl = Image.new('RGBA', (106 + padding * 2, temphl_height), (255, 255, 255, 0))
    # y_offset = padding
    # for part in temp_hl_parts:
    #     temphl.paste(part, (padding, y_offset))
    #     y_offset += part.size[1] + (padding - 85)
 
    # Create Wind Direction/Speed PNG
    wind_dir_img = create_text_image(wind_dir, (160, 45), 40, font_path)
    wind_speed_img = create_text_image(wind_speed, (160, 55), 40, font_path)

    # Assemble Wind Direction/Speed
    wind_ds_parts = [image_from_bytes(wind_dir_img), image_from_bytes(wind_speed_img)]
    wind_ds_height = sum(p.size[1] for p in wind_ds_parts) + 30  # 9px border top and bottom
    wind_ds = Image.new('RGBA', (160, wind_ds_height), (255, 255, 255, 0))  # 9px border top and bottom
    y_offset = 9
    for part in wind_ds_parts:
        wind_ds.paste(part, (0, y_offset))
        y_offset += part.size[1] + 9  # 9px border between images

    # Create Tide High/Low and Time PNG
    tide_hl_img = create_text_image(tide_hl, (170, 50), 40, font_path)
    tide_time_img = create_text_image(tide_time, (170, 60), 40, font_path)

    # Assemble Tide Information
    tide_parts = [image_from_bytes(tide_hl_img), image_from_bytes(tide_time_img)]
    tide_height = sum(p.size[1] for p in tide_parts) + 18  # 9px border top and bottom
    tide = Image.new('RGBA', (170, tide_height), (255, 255, 255, 0))  # 9px border top and bottom
    y_offset = 9
    for part in tide_parts:
        tide.paste(part, (0, y_offset))
        y_offset += part.size[1] + 9  # 9px border between images

    # Create Forecast Line PNG
    weather_icon = Image.open(weather_icon_path)
    tide_icon = Image.open(tide_icon_path)
    wind_icon = Image.open(wind_icon_path)
    humidity_icon = Image.open('./weather_icons/humidity.png')

    forecast_parts = [weather_icon, image_from_bytes(temp_img),humidity_icon, image_from_bytes(humidity_img), wind_icon, wind_ds, tide_icon, tide]
    forecast_width = sum(p.size[0] for p in forecast_parts) + 200  # 20px border left and right
    forecast = Image.new('RGBA', (forecast_width, 116), (255, 255, 255, 0))  # Height matches temperature image
    x_offset = 30
    for part in forecast_parts:
        forecast.paste(part, (x_offset, (forecast.size[1] - part.size[1]) // 2))
        x_offset += part.size[0] + 20  # 10px border between images

    # Final assembly logic with padding
    final_parts = [header, forecast]
    final_height = sum(p.size[1] for p in final_parts) + padding * (len(final_parts) - 1)
    final_image = Image.new('RGBA', (max(p.size[0] for p in final_parts), final_height), (255, 255, 255, 0))
    y_offset = 0
    for part in final_parts:
        final_image.paste(part, (0, y_offset))
        y_offset += part.size[1] + padding


    # Save final image to BytesIO
    final_img_byte_arr = io.BytesIO()
    final_image.save(final_img_byte_arr, format='PNG')
    final_img_byte_arr.seek(0)

    return final_img_byte_arr
