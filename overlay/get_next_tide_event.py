import requests
import json
import datetime
import os
from dateutil import parser
import pytz

def get_next_tide_event(station_id):
    # Set the NOAA API endpoint and parameters
    API_ENDPOINT = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    product = "predictions"
    datum = "MLLW"
    units = "english"
    time_zone = "lst_ldt"
    format_type = "json"
    interval = "hilo"
    timezone = pytz.timezone("US/Eastern")
    now = datetime.datetime.now(timezone)

    # Set the time zone to US/Eastern
    os.environ['TZ'] = "US/Eastern"

    # Format the date parameters
    params = {
        "begin_date": now.strftime('%Y%m%d'),
        "end_date": now.strftime('%Y%m%d'),
        "station": station_id,
        "product": product,
        "datum": datum,
        "units": units,
        "time_zone": time_zone,
        "format": format_type,
        "interval": interval
    }

    # Make the API request
    response = requests.get(API_ENDPOINT, params=params)
    # Check for request success
    if response.status_code != 200:
        return {"error": "Failed to fetch data from NOAA"}

    # Load the tide data from the response
    tide_data = response.json()

    # Find the next tide event
    next_event = None
    for prediction in tide_data['predictions']:
        event_time = parser.parse(prediction['t'])

        # Make event_time timezone aware
        if event_time.tzinfo is None or event_time.tzinfo.utcoffset(event_time) is None:
            event_time = timezone.localize(event_time)

        if event_time > now:
            next_event = prediction
            break

    if next_event:
        next_event_time = parser.parse(next_event['t'])
        next_event_type = next_event['type']
        tide_time = next_event_time.strftime('%I:%M %p')

        tide_hl = "High tide" if next_event_type == "H" else "Low tide"
        tide_icon = "./weather_icons/high_tide.png" if next_event_type == "H" else "./weather_icons/low_tide.png"
        
        return {
            "event_type": tide_hl,
            "event_time": tide_time,
            "tide_icon": tide_icon
        }
    else:
        return {"error": "No next event found"}

# # Function usage example:
# next_tide_event = get_next_tide_event(8531942)
# print(next_tide_event)
# next_tide_event = get_next_tide_event(8531680)
# print(next_tide_event)
# next_tide_event = get_next_tide_event(8531662)
# print(next_tide_event)
# next_tide_event = get_next_tide_event(8533391)
# print(next_tide_event)
