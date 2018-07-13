"""
Simple time checker by David. Run with `python time_checker.py` in 
the same folder as `bat_trips.json`
"""

import json
from datetime import datetime as dt

with open('bat_trips.json') as f:
    start_times = []
    end_times = []
    for i in range(24):
        start_times.append(0)
        end_times.append(0)
    data = json.load(f)
    for entry in data['data']:
        route = entry['route']['features']
        start = route[0]
        end = route[1]
        start_time = start['properties']['timestamp']
        end_time = end['properties']['timestamp']
        start_hour = dt.fromtimestamp(start_time).hour
        end_hour = dt.fromtimestamp(end_time).hour
        start_times[start_hour] += 1
        end_times[end_hour] += 1
    for i in range(24):
        print("Trips starting at hour {}: {}".format(i,start_times[i]))
        print("Trips ending at hour {}: {}".format(i,end_times[i]))
