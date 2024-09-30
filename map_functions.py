from dotenv import load_dotenv
import requests
import os
# Load environment variables
load_dotenv()

def get_travel_time(origin, destination, mode="driving"):
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        'origins': origin,
        'destinations': destination,
        'mode': mode,
        'key': os.getenv("GOOGLE_MAPS_API_KEY"),
        'units': 'imperial'
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    # print("Response:". data)

    if data['status'] == 'OK':
        travel_time = data['rows'][0]['elements'][0]['duration']['text']
        return travel_time
    else:
        return "Error fetching data"

def get_travel_time_based_on_arrival_time(origin, destination, arrival_time, mode="driving"):
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        'origins': origin,
        'destinations': destination,
        'mode': mode,
        'arrival_time': arrival_time,
        'traffic_model': 'best_guess',
        'key': os.getenv("GOOGLE_MAPS_API_KEY"),
        'units': 'imperial'
    }
    response = requests.get(url, params=params)
    data = response.json()
    # print("Response:". data)

    if data['status'] == 'OK':
        travel_time = data['rows'][0]['elements'][0]['duration_in_traffic']['text']
        return travel_time
    else:
        return "Error fetching data"
    
    
    # travel_time = get_travel_time("1600 Amphitheatre Parkway, Mountain View, CA 94043", "189 Vassar St, Cambridge, MA 02139")
    # print("Travel time without arrival time: " + travel_time)

    # travel_time = get_travel_time_based_on_arrival_time("1600 Amphitheatre Parkway, Mountain View, CA 94043", "189 Vassar St, Cambridge, MA 02139", "10:00 AM")
    # print("Travel time with arrival time: " + travel_time)