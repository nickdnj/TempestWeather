import requests
from datetime import datetime
import math

def convert_celsius_to_fahrenheit(celsius):
    if celsius is None:
        return None
    return round((celsius * 9/5) + 32)

def convert_km_to_miles(km):
    if km is None:
        return None
    return round(km * 0.621371)

def convert_kmh_to_mph(kmh):
    if kmh is None:
        return None
    return round(kmh / 1.60934)

def convert_pa_to_inhg(pa):
    if pa is None:
        return None
    return round(pa * 0.00029529983071445)

def convert_mm_to_inches(mm):
    if mm is None:
        return None
    return round(mm * 0.0393701)

def degrees_to_compass(degrees):
    if degrees is None:
        return "N"
    try:
        degrees = float(degrees)
        if degrees < 0 or degrees >= 360:
            return "N"
    except ValueError:
        return "N"
    compass_points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = int((degrees + 11.25) / 22.5)
    return compass_points[index % 16]

def extract_nws_pw_data(data):
    unit_mapping = {
        'wmoUnit:degC': ' °F',
        'wmoUnit:km_h-1': ' mph',
        'wmoUnit:m': ' miles',
        'wmoUnit:Pa': ' inHg',
        'wmoUnit:mm': ' inches',
        'wmoUnit:percent': '%',
        'wmoUnit:degree_(angle)': ''
    }
    
    extracted_data = {}
    
    for weather in data['presentWeather']:
        for key, value in weather.items():
            if value is not None:
                extracted_data[f"weather_{key}"] = value
    
    keys_with_units = ['temperature', 'dewpoint', 'windDirection', 'windSpeed', 'windGust', 'barometricPressure', 'seaLevelPressure', 'visibility', 'relativeHumidity', 'windChill', 'heatIndex']
    for key in keys_with_units:
        if data.get(key) is not None:
            value = data[key]['value']
            unitCode = data[key]['unitCode']
            if unitCode == 'wmoUnit:degC':
                value = convert_celsius_to_fahrenheit(value)
            elif unitCode == 'wmoUnit:km_h-1':
                value = convert_kmh_to_mph(value)
            elif unitCode == 'wmoUnit:m':
                value = convert_km_to_miles(value)
            elif unitCode == 'wmoUnit:Pa':
                value = convert_pa_to_inhg(value)
            elif unitCode == 'wmoUnit:mm':
                value = convert_mm_to_inches(value)
            elif unitCode == 'wmoUnit:percent':
                try:
                    value = round(value)
                except TypeError:
                    value = 0
            elif unitCode == 'wmoUnit:degree_(angle)':
                value = degrees_to_compass(value)
            
            unit = unit_mapping.get(unitCode, '')
            extracted_data[key] = f"{value}{unit}"
    
    return extracted_data

def extract_info_properties_only(data):
    extracted_info = {}
    if 'properties' in data:
        extracted_info = data['properties']
    return extracted_info

def get_weather_data_properties(location):
    print(f"Getting weather data for {location}...")

    # Replace 'YOUR_API_KEY' with your actual Google Maps Geocoding API key
    api_key = 'AIzaSyAhssTCfkOTe_cEbqrGfP3Qoo3PIW9MEgA'
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={api_key}"
    print(geocode_url)

    try:
        geocode_data = requests.get(geocode_url)
        if geocode_data.status_code // 100 == 2:
            geocode_data = geocode_data.json()
            if not geocode_data['results']:
                print("No data found")
                return {"error": "Location not found"}
            lat = geocode_data['results'][0]['geometry']['location']['lat']
            lon = geocode_data['results'][0]['geometry']['location']['lng']
            print(f"lat={lat}, lon={lon}")
        else:
            print(f"Error: Received status code {geocode_data.status_code}")
            return {"error": f"Received status code {geocode_data.status_code}"}
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}

    # Use the latitude and longitude to get the weather data from weather.gov
    gridpoint_url = f"https://api.weather.gov/points/{lat},{lon}"
    gridpoint_response = requests.get(gridpoint_url)
    if gridpoint_response.status_code // 100 == 2:
        gridpoint_data = gridpoint_response.json()
        if 'properties' not in gridpoint_data:
            return {"error": "Gridpoint data not found"}
        properties = gridpoint_data['properties']
        return properties
    else:
        return {"error": f"Received status code {gridpoint_response.status_code}"}

def get_nws_current_observations_data(location):
    print(f"Getting weather data for {location}...")

    properties = get_weather_data_properties(location)
    if 'error' in properties:
        return properties

    observation_stations_url = properties.get('observationStations')
    if not observation_stations_url:
        return {"error": "Observation stations URL not found"}

    stations_response = requests.get(observation_stations_url)
    stations_data = stations_response.json()
    
    if 'features' not in stations_data:
        return {"error": "Observation stations data not found"}
    
    closest_station = stations_data['features'][0]['properties']['stationIdentifier']
    current_observations_url = f"https://api.weather.gov/stations/{closest_station}/observations/latest"
    current_observations_response = requests.get(current_observations_url)
    current_observations_data = current_observations_response.json()

    current_observations_properties_data = extract_info_properties_only(current_observations_data)
    text_description = current_observations_properties_data.get('textDescription', 'No description available')
    nws_pw = extract_nws_pw_data(current_observations_properties_data)
    nws_pw['textDescription'] = text_description
    return nws_pw

def get_nws_forecast_data(location):
    properties = get_weather_data_properties(location)
    if 'error' in properties:
        return properties

    forecast_url = properties.get('forecast')
    if not forecast_url:
        return {"error": "Forecast URL not found"}

    forecast_response = requests.get(forecast_url)
    forecast_data = forecast_response.json()
    forecast_data_properties_data = extract_info_properties_only(forecast_data)
    return forecast_data_properties_data

def get_nws_hourly_forecast_data(location):
    properties = get_weather_data_properties(location)
    if 'error' in properties:
        return properties

    hourly_forecast_url = properties.get('forecastHourly')
    if not hourly_forecast_url:
        return {"error": "Hourly forecast URL not found"}

    hourly_forecast_response = requests.get(hourly_forecast_url)
    hourly_forecast_data = hourly_forecast_response.json()

    current_date = datetime.now()
    target_date = current_date.strftime('%Y-%m-%d')

    periods = hourly_forecast_data['properties']['periods']
    target_day_forecasts = [period for period in periods if period['startTime'].startswith(target_date)]
    return target_day_forecasts

def get_nws_alerts_data(location):
    properties = get_weather_data_properties(location)
    if 'error' in properties:
        return properties

    forecast_zone = properties.get('forecastZone')
    if not forecast_zone:
        return {"error": "Forecast zone not found"}

    alerts_url = f"https://api.weather.gov/alerts/active/zone/{forecast_zone.split('/')[-1]}"
    alerts_response = requests.get(alerts_url)
    alerts_data = alerts_response.json()
    return alerts_data
