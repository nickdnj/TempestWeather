# filename: get_weather_data.py

import requests
from datetime import datetime

def extract_info_properties_only(data):
    # Create a new dictionary to hold the extracted information
    extracted_info = {}
    
    # Check if 'properties' key exists and add it to the extracted_info
    if 'properties' in data:
        extracted_info = data['properties']
    
    return extracted_info

# The function now only extracts the 'properties' section, ignoring 'geometry' and other sections.
# Sample usage (Commented out to prevent execution):
'''
sample_data = {
    '@context': [...],
    'id': 'https://api.weather.gov/stations/KBLM/observations/2024-02-22T13:56:00+00:00',
    'type': 'Feature',
    'geometry': {...},
    'properties': {...}  # Detailed information
}

# result = extract_info_properties_only(sample_data)
# print(result)
'''


def get_weather_data(location):
    # Use a geocoding service to get latitude and longitude from the location
    geocode_url = f"https://nominatim.openstreetmap.org/search?format=json&q={location}"
    geocode_response = requests.get(geocode_url)
    geocode_data = geocode_response.json()
    
    if not geocode_data:
        return {"error": "Location not found"}
    
    # Get the first result
    lat = geocode_data[0]['lat']
    lon = geocode_data[0]['lon']
    
    # Use the latitude and longitude to get the weather data from weather.gov
    gridpoint_url = f"https://api.weather.gov/points/{lat},{lon}"
    gridpoint_response = requests.get(gridpoint_url)
    gridpoint_data = gridpoint_response.json()
    
    if 'properties' not in gridpoint_data:
        return {"error": "Gridpoint data not found"}
    
    # Extract the required URLs from the gridpoint data
    properties = gridpoint_data['properties']
    forecast_url = properties['forecast']
    hourly_forecast_url = properties['forecastHourly']
    observation_stations_url = properties['observationStations']
    forecast_zone = properties['forecastZone']
    
    # Get the current observations from the nearest observation station
    stations_response = requests.get(observation_stations_url)
    stations_data = stations_response.json()
    
    if 'features' not in stations_data:
        return {"error": "Observation stations data not found"}
    
    # Get the closest station
    closest_station = stations_data['features'][0]['properties']['stationIdentifier']
    
    current_observations_url = f"https://api.weather.gov/stations/{closest_station}/observations/latest"
    current_observations_response = requests.get(current_observations_url)
    current_observations_data = current_observations_response.json()
    current_observations_properties_data = extract_info_properties_only(current_observations_data)
    print("COPD",current_observations_properties_data)
    print("COPD END")

    
    # Get the forecast
    forecast_response = requests.get(forecast_url)
    forecast_data = forecast_response.json()
    
    # Get the hourly forecast
    hourly_forecast_response = requests.get(hourly_forecast_url)
    hourly_forecast_data = hourly_forecast_response.json()

    # The date you're interested in (YYYY-MM-DD format)
    # Get the current date
    current_date = datetime.now()

    # Format the date as a string in the format 'YYYY-MM-DD'
    target_date = current_date.strftime('%Y-%m-%d')

    # Parse the periods from the JSON data
    periods = hourly_forecast_data['properties']['periods']

    # Filter periods to include only those that start on the target date
    target_day_forecasts = [period for period in periods if period['startTime'].startswith(target_date)]

# Optional: Convert to your local timezone if necessary
# You might need to install the pytz module for timezone conversions
# import pytz
# local_timezone = pytz.timezone('Your/Timezone')
# target_day_forecasts_local = [{
#     **period,
#     'startTime': datetime.fromisoformat(period['startTime']).astimezone(local_timezone),
#     'endTime': datetime.fromisoformat(period['endTime']).astimezone(local_timezone)
# } for period in target_day_forecasts]


    
    # Get the alerts for the forecast zone
    alerts_url = f"https://api.weather.gov/alerts/active/zone/{forecast_zone.split('/')[-1]}"
    alerts_response = requests.get(alerts_url)
    alerts_data = alerts_response.json()
    
    #print(current_observations_data, hourly_forecast_data,forecast_data, alerts_data  )
    # Compile all the data into a single JSON object
    weather_data = {
        "current_observations": current_observations_data
 #       "hourly_forecast": hourly_forecast_data,
 #       "hourly_forecast": target_day_forecasts,
 #       "forecast": forecast_data,
 #       "alerts": alerts_data
    }

    return weather_data


# Example usage:
#location = "New York, NY"
# location = "Monmouth Beach, NJ"

# weather_data = get_weather_data(location)
