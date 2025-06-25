# filename: get_water_temperature.py
import requests

def get_water_temperature(station_id):
    # Base URL for the API endpoint
    base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    
    # Parameters for the API query
    params = {
        'date': 'latest',
        'station': station_id,
        'product': 'water_temperature',
        'datum': 'MLLW',
        'time_zone': 'lst_ldt',
        'units': 'english',
        'application': 'd3marco',
        'format': 'json'
    }
    
    # Perform the API request
    response = requests.get(base_url, params=params)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Extract the required information
        water_temperature = {
            'StationId': data['metadata']['id'],
            'name': data['metadata']['name'],
            'lat': data['metadata']['lat'],
            'lon': data['metadata']['lon'],
            'water_temperature_time': data['data'][0]['t'],
            'water_temperature': data['data'][0]['v']
        }
        
        # Return the water_temp JSON object
        return water_temperature
    else:
        # Handle the case where the API request failed
        print(f"Failed to retrieve data: {response.status_code}")
        return None

# Example usage:
#station_id = "8531680"
#result = get_water_temperature(station_id)
#ßprint(result)