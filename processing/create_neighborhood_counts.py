"""
Short script to automate creation of geojson file to visualize neighborhood
level counts of available bikes.

Written by: David Klinger
"""

from measure import measure
import argparse
import fiona
import pprint
import json
import pyproj
import sqlalchemy
import datetime
import time
import shapely.geometry
import pandas

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
args = parser.parse_args()

# connect to database
def connect(user, password, db, host, port):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

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

def get_count(con,start,end,area,device):
    print("Querying.")
    command = """
              SELECT * FROM "availability" 
              WHERE ((start_time < {} AND end_time > {}) OR
                     (start_time < {} AND end_time > {}) OR
                     (start_time > {} AND end_time < {})) AND
                     device_type = '{}'
              ORDER BY start_time, end_time
              """.format(start, start, end, end, start, end, device)
    db = pandas.read_sql(command,con,index_col=None)
    print("Query done.")
    n = measure(db,start,end,area)
    return n

def read_poly(poly, original, dest):
    interior = []
    exterior = []
    for p in poly:
        new_list = []
        for x,y in p:
            x_prime, y_prime = pyproj.transform(original, dest, x, y)
            p = (x_prime, y_prime)
            new_list.append(p)
        if exterior == []:
            exterior = new_list
        else:
            interior.append(new_list)
    final_area = shapely.geometry.Polygon(exterior, interior)
    return final_area

area = fiona.open("la_neighborhoods.shp")
original = pyproj.Proj(area.crs, preserve_units=True)
dest = pyproj.Proj(init='epsg:4326')
for i in range(24):
    start = datetime.datetime(2018,8,1,i,0,0)
    print("HOUR {}".format(i))
    start_timestamp = time.mktime(start.timetuple())
    end_timestamp = time.mktime(datetime.datetime(2018,8,1,i+1,0,0).timetuple())
    d = {}
    d['type'] = 'FeatureCollection'
    d['features'] = []
    for a in area:
        print("AREA {} ({} of {})".format(a['properties']['COMTY_NAME'],a['id'],len(area)))
        f = {}
        f['type'] = 'Feature'
        f['geometry'] = {}
        f['geometry']['type'] = 'Polygon'
        f['geometry']['coordinates'] = []
        for l in a['geometry']['coordinates']:
            li = []
            for x,y in l:
                x_prime, y_prime = pyproj.transform(original, dest, x, y)
                li.append([x_prime,y_prime])
            f['geometry']['coordinates'].append(li)
        f['properties'] = {}
        f['properties']['name'] = a['properties']['COMTY_NAME']
        f['properties']['id'] = a['id']
        neighborhood = read_poly(a['geometry']['coordinates'],original,dest)
        f['properties']['count'] = get_count(con,start_timestamp,
                end_timestamp,neighborhood,"scooter")
        d['features'].append(f)
    print("writing to file")
    with open('neighborhood_counts/{}_{}.geojson'.format(start,i),'w') as file:
        json.dump(obj=d,fp=f,indent=4)
    print("done")
    print("\n\n\n")

