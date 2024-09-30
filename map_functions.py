from dotenv import load_dotenv
import requests
import os
import time
from datetime import datetime

# Load environment variables
load_dotenv()

def sanitize_time(time_str):
    if time_str == "now":
        return "now"
    try:
        # Parse the ISO 8601 format
        dt = datetime.fromisoformat(time_str)
        # Convert to Unix timestamp
        timestamp = int(dt.timestamp())
        # Ensure the time is in the future
        if timestamp <= int(time.time()):
            raise ValueError("Time must be in the future")
        return timestamp
    except ValueError as e:
        return {"error": str(e)}
        
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
    url = "https://maps.googleapis.com/maps/api/directions/json"
    
    sanitized_time = sanitize_time(arrival_time)
    if isinstance(sanitized_time, dict) and "error" in sanitized_time:
        return sanitized_time["error"]
    
    params = {
        'origin': origin,
        'destination': destination,
        'mode': mode,
        'arrival_time': sanitized_time,
        'key': os.getenv("GOOGLE_MAPS_API_KEY"),
        'units': 'imperial'
    }
    response = requests.get(url, params=params)
    data = response.json()
    # print("Response:", data)

    if data['status'] == 'OK':
        route = data['routes'][0]
        leg = route['legs'][0]
        duration = leg['duration']['text']
        return duration
    else:
        return "Error fetching arrival time"
    
def get_travel_time_based_on_departure_time(origin, destination, departure_time, mode="driving"):
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
    
    sanitized_time = sanitize_time(departure_time)
    if isinstance(sanitized_time, dict) and "error" in sanitized_time:
        return sanitized_time["error"]
    
    params = {
        'origins': origin,
        'destinations': destination,
        'mode': mode,
        'departure_time': sanitized_time,
        'traffic_model': 'best_guess',
        'key': os.getenv("GOOGLE_MAPS_API_KEY"),
        'units': 'imperial'
    }
    response = requests.get(url, params=params)
    data = response.json()
    # print("Response:", data)

    if data['status'] == 'OK':
        travel_time = data['rows'][0]['elements'][0]['duration_in_traffic']['text']
        return travel_time
    else:
        return "Error fetching departure time"

    
    # travel_time = get_travel_time("1600 Amphitheatre Parkway, Mountain View, CA 94043", "189 Vassar St, Cambridge, MA 02139")
    # print("Travel time without arrival time: " + travel_time)

    # travel_time = get_travel_time_based_on_arrival_time("1600 Amphitheatre Parkway, Mountain View, CA 94043", "189 Vassar St, Cambridge, MA 02139", "10:00 AM")
    # print("Travel time with arrival time: " + travel_time)