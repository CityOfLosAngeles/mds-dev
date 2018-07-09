import psycopg2
import pandas as pd
import sqlalchemy
import json 
import requests 
import pprint
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("user", type=str, 
        help="username to access postgresql database")
parser.add_argument("password", type=str, 
        help="password to access postgresql database")
parser.add_argument("database", type=str, 
        help="database name")
parser.add_argument("--host","-H", type=str, 
        help="database host")
parser.add_argument("--port","-p", type=str, 
        help="database port")
parser.add_argument("filename", type=str, 
        help="path to file that contains list of urls to pull from, as well as their types")
args = parser.parse_args()



def connect(user, password, db, host, port):
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

def get_status_change_data(url,con):
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
         'event_type':[],
         'reason':[],
         'event_time':[],
         'location':[],
         'battery_pct':[],
         'associated_trips':[]}
    for i in range(len(datas)):
        entry = datas[i]
        for k in d:
            if k in entry:
                if k=='location':
                    x = entry[k]['coordinates'][0]
                    y = entry[k]['coordinates'][1]
                    point = str((x,y))
                    d[k].append(point)
                else:
                    d[k].append(entry[k])
            else:
                d[k].append(None)
    df = pd.DataFrame(data=d)
    df.to_sql('status_change',con,if_exists='append',index=False)

user = args.user
password = args.password
db = args.database
host = "localhost"
if args.host is not None:
    host = args.host
port = 5432
if args.port is not None:
    port = args.port
con = connect(user,password,db,host,port)

with open(args.filename) as f:
    lines = f.readlines()
    for line in lines:
        entries = line.strip().split(', ')
        print("Writing data: {} - {}".format(entries[0],entries[1]))
        if entries[1] == 'status_changes':
            print("Writing status changes.")
            get_status_change_data(entries[0],con)
        elif entries[1] == 'trips':
            print("Writing trips.")
            get_trip_data(entries[0],con)
        print("Done")
        print()

