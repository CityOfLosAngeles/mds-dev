"""
This file will generate json files for each of our fake mobility providers 
with trip data following the mobility data specifications

Also uses District 10 boundary to create service area json files for both
companies.

Author: David Klinger
"""

import pandas as pd
import numpy
import json
import fiona
import pprint
import shapely.geometry
import pyproj
import random
import math
import datetime
import time
import uuid
import shapely.wkt
import json

# generate district 10 boundary using gps coordinates
# also used to make json for service areas
bounds = fiona.open('CouncilDistricts.shp')
original = pyproj.Proj(bounds.crs)
dest = pyproj.Proj(init='epsg:4326')
polygons = []
polygons_list = []
for poly in bounds[11]['geometry']['coordinates']: # get district 10
    polygon = [] # eventual converted polygon
    polygon_lists = []
    for x,y in poly:
        x_prime,y_prime = pyproj.transform(original,dest,x,y) # transform point
        p = (x_prime,y_prime)
        polygon.append(p)
        polygon_lists.append([x_prime,y_prime])
    polygons.append(shapely.geometry.Polygon(polygon))
    polygons_list.append(polygon_lists)
boundary = shapely.geometry.MultiPolygon(polygons) # our final boundary

# write service area jsons
def make_service_area(company_name):
    data = {}
    data['data'] = []
    d = {}
    d['operator_name'] = company_name
    d['service_area_id'] = str(uuid.uuid4())
    d['service_start_date'] = time.mktime(datetime.datetime(2018,8,1,6,0,0,0)
            .timetuple())
    d['service_end_date'] = time.mktime(datetime.datetime(2018,9,1,3,0,0,0)
            .timetuple())
    d['service_area'] = {}
    d['service_area']['type']='MultiPolygon'
    d['service_area']['coordinates'] = polygons_list
    data['data'].append(d)
    f = open(company_name+"_service_area"+".json",'w')
    f.write(json.dumps(data,indent=4,separators=(',',': ')))

make_service_area("bat")
make_service_area("lemon")

# returns a random point somewhere in the city of LA
def get_random_point():
    minx, miny, maxx, maxy = boundary.bounds
    pnt = shapely.geometry.Point(random.uniform(minx,maxx),
            random.uniform(miny,maxy))
    while not boundary.contains(pnt):
        pnt = shapely.geometry.Point(random.uniform(minx,maxx),
                random.uniform(miny,maxy))
    return pnt

# returns a point at a given distance from another point
# pnt: a point
# dist: distance, in meters
def get_point_nearby(pnt, dist):
    angle = random.uniform(0,2*math.pi)
    R = 6378100
    x = pnt.x
    y = pnt.y
    lat1 = math.radians(y)
    lon1 = math.radians(x)
    lat2 = math.asin(math.sin(lat1)*math.cos(dist/R)+
            math.cos(lat1)*math.sin(dist/R)*math.cos(angle))
    lon2 = lon1 + math.atan2(math.sin(angle)*math.sin(dist/R)*math.cos(lat1),
            math.cos(dist/R)-math.sin(lat1)*math.sin(lat2))
    return shapely.geometry.Point(math.degrees(lon2),math.degrees(lat2))

# generates a random string for the fake url
def random_string():
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    s = ""
    for i in range(8):
        j = int(random.uniform(0,len(chars)))
        s += chars[j]
    return s

# returns a max wait time, in seconds
# depends on time, which should be unix time
def wait_time_max(time):
    dt = datetime.datetime.fromtimestamp(time)
    hours = dt.hour
    if hours < 3:
        hours += 24
    hours -= 6
    hours += dt.minute/60 + dt.second/3600
    return 1800*math.cos(hours*(math.pi/10)) + 1800

def day_over(end_time):
    dt = datetime.datetime.fromtimestamp(end_time)
    return dt.hour > 1 and dt.hour < 6

trip_columns = ['company_name',
                'device_type',
                'trip_id',
                'trip_duration',
                'trip_distance',
                'start_point',
                'end_point',
                'accuracy',
                'route',
                'sample_rate',
                'device_id',
                'start_time',
                'end_time',
                'parking_verification',
                'standard_cost',
                'actual_cost']

status_change_columns = ['company_name',
                        'device_type',
                        'device_id',
                        'event_type',
                        'reason',
                        'event_time',
                        'location',
                        'battery_pct',
                        'associated_trips']

def generate_day_data(day,device_id,company_name,device_type,url):
    trip_data = []
    status_change_data = []
    battery_pct = 100
    end_time = time.mktime(datetime.datetime(2018,8,day,6,0,0,0).timetuple())
    end_point = get_random_point()
    end_day_pick_up = False # flag
    status_change_data.append([company_name,
                               device_type,
                               device_id,
                               'available',
                               'service_start',
                               end_time,
                               end_point,
                               battery_pct,
                               None])
    while not day_over(end_time):
        if not boundary.contains(end_point):
            # pick up
            status_change_data.append([company_name,
                                       device_type,
                                       device_id,
                                       'removed',
                                       'out_of_service_area_pick_up',
                                       end_time,
                                       end_point,
                                       battery_pct,
                                       None])
            wait_time = random.uniform(10*60,2*60*60)
            end_point = get_random_point()
            end_time = end_time + wait_time
            # drop off
            status_change_data.append([company_name,
                                       device_type,
                                       device_id,
                                       'available',
                                       'out_of_service_area_drop_off',
                                       end_time,
                                       end_point,
                                       battery_pct,
                                       None])
        wait_time = random.uniform(0,wait_time_max(end_time))
        start_time = end_time + wait_time
        start_point = end_point
        if day_over(start_time):
            status_change_data.append([company_name,
                                       device_type,
                                       device_id,
                                       'removed',
                                       'service_end',
                                       start_time,
                                       start_point,
                                       battery_pct,
                                       None])
            end_day_pick_up = True
            end_time = start_time
        else:
            trip_id = uuid.uuid4()
            trip_duration = numpy.random.chisquare(5)*1.2*60 # in seconds
            # we will assume scooters go about 4 m/s
            trip_distance = trip_duration*4
            # 20% penalty to account for roads
            end_point = get_point_nearby(start_point,trip_distance*0.8)
            end_time = start_time + trip_duration
            standard_cost = math.floor(trip_duration/60)
            actual_cost = (100 + (math.floor(trip_duration/60)-1)*15)
            parking_verification = url+"/images/" + random_string()
            status_change_data.append([company_name,
                                       device_type,
                                       device_id,
                                       'reserved',
                                       'user_pick_up',
                                       start_time,
                                       start_point,
                                       battery_pct,
                                       None])
            battery_pct -= 0.001*trip_duration
            status_change_data.append([company_name,
                                       device_type,
                                       device_id,
                                       'available',
                                       'user_drop_off',
                                       end_time,
                                       end_point,
                                       battery_pct,
                                       None])
            trip_data.append([company_name,
                              device_type,
                              device_id,
                              trip_duration,
                              trip_distance,
                              start_point,
                              end_point,
                              5,
                              None,
                              None,
                              device_id,
                              int(start_time),
                              int(end_time),
                              parking_verification,
                              standard_cost,
                              actual_cost])
    if not end_day_pick_up:
        status_change_data.append([company_name,
                                   device_type,
                                   device_id,
                                   'removed',
                                   'service_end',
                                   start_time,
                                   start_point,
                                   battery_pct,
                                   None])
        end_day_pick_up = True
    return trip_data,status_change_data

def make_dataframes(company_name, device_type,url,num_units):
    trip_data = []
    status_change_data = []
    for i in range(0,num_units):
        print("Generating device {}: {} of {}".format(company_name,i,num_units-1))
        device_id = uuid.uuid4()
        for j in range(1,32):
            t_data, sc_data = generate_day_data(j,device_id,
                    company_name,device_type,url)
            trip_data += t_data
            status_change_data += sc_data
    trip_df = pd.DataFrame(trip_data,columns=trip_columns)
    status_change_df = pd.DataFrame(status_change_data,
            columns=status_change_columns)
    return trip_df, status_change_df

# convert trip data into json
def trip_convert(db,output_file):
    db = db.fillna('')
    num_rows = db.shape[0]
    data = {}
    data['data'] = []
    for i in db.index:
        if i%5000==0:
            print("{} of {}".format(i,num_rows))
        d = db.loc[i].to_dict()
        start_loc = d['start_point']
        end_loc = d['end_point']
        d['start_point'] = {}
        d['start_point']['type'] = "Point"
        d['start_point']['coordinates'] = [start_loc.x,start_loc.y]
        d['end_point'] = {}
        d['end_point']['type'] = "Point"
        d['end_point']['coordinates'] = [end_loc.x,end_loc.y]
        if d['route']=='':
            d.pop('route',None)
        if d['sample_rate']=='':
            d.pop('sample_rate',None)
        d['device_id'] = str(d['device_id'])
        d['trip_id'] = str(d['trip_id'])
        d['trip_duration'] = float(d['trip_duration'])
        d['trip_distance'] = float(d['trip_distance'])
        d['accuracy'] = float(d['accuracy'])
        d['start_time'] = float(d['start_time'])
        d['end_time'] = float(d['end_time'])
        d['standard_cost'] = int(d['standard_cost'])
        d['actual_cost'] = int(d['actual_cost'])
        data['data'].append(d)
    result = json.dumps(data,indent=4,separators=(',',': '))
    f = open(output_file,'w')
    f.write(result)

# convert availability data into json
def status_change_convert(db,output_file):
    db = db.fillna('')
    num_rows = db.shape[0]
    data = {}
    data['data'] = []
    for i in db.index:
        if i%5000==0:
            print("{} of {}".format(i,num_rows))
        d = db.loc[i].to_dict()
        if d['associated_trips']=='':
            d.pop('associated_trips',None)
        d['device_id'] = str(d['device_id'])
        start_loc = d['location']
        d['location'] = {}
        d['location']['type'] = "Point"
        d['location']['coordinates'] = [start_loc.x,start_loc.y]
        d['event_time'] = int(d['event_time'])
        d['battery_pct'] = float(d['battery_pct'])
        data['data'].append(d)
    result = json.dumps(data,indent=4,separators=(',',': '))
    f = open(output_file,'w')
    f.write(result)

print("Generating bat data.")
btrips,bsc = make_dataframes("Bat","scooter","bat.co",100)
print("Done.")

print("Generating Lemon data.")
ltrips,lsc = make_dataframes("Lemon","scooter","lemonbike.com",100)
print("Done.")

print("Writing Bat Trips JSON")
trip_convert(btrips,'bat_trips.json')
print("Done.")

print("Writing Lemon Trips JSON")
trip_convert(ltrips,'lemon_trips.json')
print("Done.")

print("Writing Bat Status Change JSON")
status_change_convert(bsc,'bat_status_change.json')
print("Done.")
print("Writing Lemon Status Change JSON")
status_change_convert(lsc,'lemon_status_change.json')
print("Done.")
