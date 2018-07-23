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
import os

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
                'device_id',
                'trip_duration',
                'trip_distance',
                'route',
                'accuracy',
                'trip_id',
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

def make_route(start_point, end_point, start_time, end_time):
    route = {}
    route["type"] = "FeatureCollection"
    route["features"] = [make_feature(start_point, start_time), 
                         make_feature(end_point, end_time)]
    return route

def make_feature(point, time):
    feature = {}
    feature["type"] = "Feature"
    feature["properties"] = {"timestamp" : int(time)}
    feature["geometry"] = {}
    feature["geometry"]["type"] = "Point"
    feature["geometry"]["coordinates"] = [point.x, point.y]
    return feature

# generates one days worth of data for one device
def generate_day_data(day,device_id,company_name,device_type,url):
    trip_data = []
    status_change_data = []
    battery_pct = 100
    end_time = time.mktime(datetime.datetime(2018,8,day,6,0,0,0).timetuple())
    end_point = get_random_point()
    end_day_pick_up = False # flag
    sc_data = {}
    sc_data['company_name'] = company_name
    sc_data['device_type'] = device_type
    sc_data['device_id'] = device_id
    sc_data['event_type'] = 'available'
    sc_data['reason'] = 'service_start'
    sc_data['event_time'] = end_time
    sc_data['location'] = end_point
    sc_data['battery_pct'] = battery_pct
    sc_data['associated_trips'] = None
    status_change_data.append(sc_data)

    while not day_over(end_time):
        if not boundary.contains(end_point):
            # pick up
            sc_data = {}
            sc_data['company_name'] = company_name
            sc_data['device_type'] = device_type
            sc_data['device_id'] = device_id
            sc_data['event_type'] = 'removed'
            sc_data['reason'] = 'out_of_service_area_pick_up'
            sc_data['event_time'] = end_time
            sc_data['location'] = end_point
            sc_data['battery_pct'] = battery_pct
            sc_data['associated_trips'] = None
            status_change_data.append(sc_data)

            wait_time = random.uniform(10*60,2*60*60)
            end_point = get_random_point()
            end_time = end_time + wait_time
            # drop off
            sc_data = {}
            sc_data['company_name'] = company_name
            sc_data['device_type'] = device_type
            sc_data['device_id'] = device_id
            sc_data['event_type'] = 'available'
            sc_data['reason'] = 'out_of_service_area_drop_off'
            sc_data['event_time'] = end_time
            sc_data['location'] = end_point
            sc_data['battery_pct'] = battery_pct
            sc_data['associated_trips'] = None
            status_change_data.append(sc_data)
            

        wait_time = random.uniform(0,wait_time_max(end_time))
        start_time = end_time + wait_time
        start_point = end_point
        if day_over(start_time):
            sc_data = {}
            sc_data['company_name'] = company_name
            sc_data['device_type'] = device_type
            sc_data['device_id'] = device_id
            sc_data['event_type'] = 'removed'
            sc_data['reason'] = 'service_end'
            sc_data['event_time'] = start_time
            sc_data['location'] = start_point
            sc_data['battery_pct'] = battery_pct
            sc_data['associated_trips'] = None
            status_change_data.append(sc_data)
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
            sc_data = {}
            sc_data['company_name'] = company_name
            sc_data['device_type'] = device_type
            sc_data['device_id'] = device_id
            sc_data['event_type'] = 'reserved'
            sc_data['reason'] = 'user_pick_up'
            sc_data['event_time'] = start_time
            sc_data['location'] = start_point
            sc_data['battery_pct'] = battery_pct
            sc_data['associated_trips'] = None
            status_change_data.append(sc_data)


            battery_pct -= 0.001*trip_duration
            sc_data = {}
            sc_data['company_name'] = company_name
            sc_data['device_type'] = device_type
            sc_data['device_id'] = device_id
            sc_data['event_type'] = 'available'
            sc_data['reason'] = 'user_drop_off'
            sc_data['event_time'] = end_time
            sc_data['location'] = end_point
            sc_data['battery_pct'] = battery_pct
            sc_data['associated_trips'] = None
            status_change_data.append(sc_data)

            route = make_route(start_point, end_point, start_time, end_time)
            t_data = {}
            t_data['company_name'] = company_name
            t_data['device_type'] = device_type
            t_data['device_id'] = device_id
            t_data['trip_duration'] = trip_duration
            t_data['trip_distance'] = trip_distance
            t_data['route'] = route
            t_data['accuracy'] = 5
            t_data['trip_id'] = trip_id
            t_data['parking_verification'] = parking_verification
            t_data['standard_cost'] = standard_cost
            t_data['actual_cost'] = actual_cost
            trip_data.append(t_data)

            
    if not end_day_pick_up:
        sc_data = {}
        sc_data['company_name'] = company_name
        sc_data['device_type'] = device_type
        sc_data['device_id'] = device_id
        sc_data['event_type'] = 'removed'
        sc_data['reason'] = 'service_end'
        sc_data['event_time'] = start_time
        sc_data['location'] = start_point
        sc_data['battery_pct'] = battery_pct
        sc_data['associated_trips'] = None
        status_change_data.append(sc_data)
        end_day_pick_up = True

    return trip_data,status_change_data

# creates dataframe using day data
# creates num_units devices, generating data for their trips for a month
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
    return trip_data, status_change_data

# convert trip data into json
def trip_convert(db,output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    pages = []
    data = {}
    i = 0
    num_rows = len(db)
    page = 1
    data['data'] = []
    data['first'] ="http://localhost:8000/" + output_folder + "/" + str(page) + ".json"
    data['prev'] = "null"
    for d in db:
        if i%50==0 and i>0:
            pages.append(data)
            page += 1
            data = {}
            data['data'] = []
            data['first'] = "http://localhost:8000/" + output_folder + "/1.json"
            data['prev'] = "http://localhost:8000/" + output_folder + "/" + str(page-1) + ".json"
        if i%5000==0:
            print("{} of {}".format(i,num_rows))
        d['device_id'] = str(d['device_id'])
        d['trip_id'] = str(d['trip_id'])
        d['trip_duration'] = float(d['trip_duration'])
        d['trip_distance'] = float(d['trip_distance'])
        d['accuracy'] = float(d['accuracy'])
        d['standard_cost'] = int(d['standard_cost'])
        d['actual_cost'] = int(d['actual_cost'])
        data['data'].append(d)
        i+=1
    last = page-1
    for i in range(len(pages)):
        if i<len(pages)-1:
            pages[i]['next'] = "http://localhost:8000/" + output_folder + "/" + str(i+2) + ".json"
        else:
            pages[i]['next'] = "null"
        pages[i]['last'] = "http://localhost:8000/" + output_folder + "/" + str(last) + ".json" 
        result = json.dumps(pages[i],indent=4,separators=(',',': '))
        f = open(output_folder + "/" + str(i+1) + ".json",'w')
        f.write(result)

# convert status change data into json
def status_change_convert(db,output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    pages = []
    data = {}
    i = 0
    num_rows = len(db)
    page = 1
    first = output_folder + "/" + str(page) + ".json"
    data['data'] = []
    data['first'] = "http://localhost:8000/" + output_folder + "/" + str(page) + ".json"
    data['prev'] = "null"
    for d in db:
        if i%50==0 and i>0:
            pages.append(data)
            page += 1
            data = {}
            data['data'] = []
            data['first'] = "http://localhost:8000/" + output_folder + "/1.json"
            data['prev'] = "http://localhost:8000/" + output_folder + "/" + str(page-1) + ".json"
        if i%5000==0:
            print("{} of {}".format(i,num_rows))
        d['device_id'] = str(d['device_id'])
        start_loc = d['location']
        d['location'] = {}
        d['location']['type'] = "Point"
        d['location']['coordinates'] = [start_loc.x,start_loc.y]
        d['event_time'] = int(d['event_time'])
        d['battery_pct'] = float(d['battery_pct'])
        data['data'].append(d)
        i += 1
    last = page-1
    for i in range(len(pages)):
        if i<len(pages)-1:
            pages[i]['next'] = "http://localhost:8000/" + output_folder + "/" + str(i+2) + ".json"
        else:
            pages[i]['next'] = "null"
        pages[i]['last'] = "http://localhost:8000/" + output_folder + "/" + str(last) + ".json"
        result = json.dumps(pages[i],indent=4,separators=(',',': '))
        f = open(output_folder + "/" + str(i+1) + ".json",'w')
        f.write(result)

make_service_area("bat")
make_service_area("lemon")

print("Generating bat data.")
btrips,bsc = make_dataframes("Bat","scooter","bat.co",100)
print("Done.")

print("Generating Lemon data.")
ltrips,lsc = make_dataframes("Lemon","scooter","lemonbike.com",100)
print("Done.")

print("Writing Bat Trips JSON")
trip_convert(btrips,'bat_trips')
print("Done.")

print("Writing Bat Status Change JSON")
status_change_convert(bsc,'bat_status_change')
print("Done.")

print("Writing Lemon Trips JSON")
trip_convert(ltrips,'lemon_trips')
print("Done.")

print("Writing Lemon Status Change JSON")
status_change_convert(lsc,'lemon_status_change')
print("Done.")
