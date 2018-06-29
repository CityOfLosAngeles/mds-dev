import psycopg2
import pandas as pd
import sqlalchemy
import json
import requests
import pprint

def connect(user, password, db, host='localhost', port=5432):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

def get_trip_data(url,con):
    try:
        data = requests.get(url)
    except requests.exceptions.RequestException as error:
        print(error)
        return None
    datas = data.json()['data']
    # initialize rows
    d = {'company_name':[],
         'device_type':[],
         'trip_id':[],
         'trip_duration':[],
         'trip_distance':[],
         'start_point':[],
         'end_point':[],
         'accuracy':[],
         'route':[],
         'sample_rate':[],
         'device_id':[],
         'start_time':[],
         'end_time':[],
         'parking_verification':[],
         'standard_cost':[],
         'actual_cost':[]}
    for i in range(len(datas)):
        entry = datas[i]
        for k in d:
            if k in entry:
                if k=='start_point' or k=='end_point':
                    x = entry[k]['coordinates'][0]
                    y = entry[k]['coordinates'][1]
                    point = str((x,y))
                    d[k].append(point)
                else:
                    d[k].append(entry[k])
            else:
                d[k].append(None)
    df = pd.DataFrame(data=d)
    df.to_sql('trips',con,if_exists='append',index=False)

def get_availability_data(url,con):
    try:
        data = requests.get(url)
    except requests.exceptions.RequestException as error:
        print(error)
        return None
    datas = data.json()['data']
    # initialize rows
    d = {'company_name':[],
         'device_type':[],
         'device_id':[],
         'availability_start_time':[],
         'availability_end_time':[],
         'placement_reason':[],
         'allowed_placement':[],
         'pickup_reason':[],
         'associated_trips':[]}
    for i in range(len(datas)):
        entry = datas[i]
        for k in d:
            if k in entry:
                d[k].append(entry[k])
            else:
                d[k].append(None)
    df = pd.DataFrame(data=d)
    df.to_sql('availability',con,if_exists='append',index=False)

con = connect("david","password","transit")

print("Writing lemon trip data.")
get_trip_data("http://localhost:8000/lemon_trips.json",con)
print("Writing bat trip data.")
get_trip_data("http://localhost:8000/bat_trips.json",con)
print("writing lemon availability data.")
get_availability_data("http://localhost:8000/lemon_availability.json",con)
print("writing bat availability data.")
get_availability_data("http://localhost:8000/bat_availability.json",con)

