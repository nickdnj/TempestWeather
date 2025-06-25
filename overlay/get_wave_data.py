# filename: get_wave_data.py
import requests
import json

def get_wave_data(buoy_name , buoy_id):
    buoy_name = buoy_name

    url = f"https://www.ndbc.noaa.gov/data/realtime2/{buoy_id}.spec"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code

        # Parse the text response into lines
        lines = response.text.splitlines()
        # Find the line with the data headers
        header_line_index = next(i for i, line in enumerate(lines) if line.startswith("#YY"))
        data_header = lines[header_line_index].split()
        
        # Find the first line of actual data after the header
        for i in range(header_line_index + 1, len(lines)):
            if not lines[i].startswith('#'):
                data_values = lines[i].split()
                break

        # Map the headers to values
        data = dict(zip(data_header, data_values))

        # Select the relevant wave data
            # Significant Wave Height (WVHT): 2.0 ft
            # Swell Height (SwH): 0.7 ft
            # Swell Period (SwP): 5.9 sec
            # Swell Direction (SwD): SSE
            # Wind Wave Height (WWH): 1.6 ft
            # Wind Wave Period (WWP): 3.2 sec
            # Wind Wave Direction (WWD): E
            #Average Wave Period (APD): 3.3 sec
        wave_data = {
            "Significant_Wave_Height": data.get("WVHT", None) + " m" if data.get("WVHT", None) else None,
            "Swell_Height": data.get("SwH", None) + " m" if data.get("SwH", None) else None,
            "Swell_Period": data.get("SwP", None) + " sec" if data.get("SwP", None) else None,
            "Swell_Direction": data.get("SwD", None),
            "Wind_Wave_Height": data.get("WWH", None) + " m" if data.get("WWH", None) else None,
            "Wind_Wave_Period": data.get("WWP", None) + " sec" if data.get("WWP", None) else None,
            "Wind_Wave Direction": data.get("WWD", None) + " degT" if data.get("WWD", None) else None,
            "Average_Wave_Period": data.get("APD", None) + " sec" if data.get("APD", None) else None,
        }
        # Convert to JSON
        #print(buoy_id)
        #wave_data_json = json.dumps(wave_data)
        #return wave_data_json
        return wave_data

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

# Example usage:
#print(get_wave_data("Sandy Hook", '44065'))