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
import pandas
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
    hours -= 5
    if hours < 1:
        hours += 1
    hours += dt.minute/60 + dt.second/3600
    return 1800*math.cos(hours*(10/math.pi)) + 1800

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

availability_columns = ['company_name',
                        'device_type',
                        'device_id',
                        'availability_start_time',
                        'availability_end_time',
                        'placement_reason',
                        'allowed_placement',
                        'pickup_reason',
                        'associated_trips']
            

# not going a complete agent based simulation
# the day starts at 6 am
# the day end at 2 am
# between 2 and 6 the scooters are charged or something
# they start the next day at new random positions
# returns a dataframe with the trips
def make_dataframes(company_name,device_type,url,num_units):
    trip_data = []
    availability_data = []
    for i in range(0,num_units):
        accuracy = 5
        print("Generating device {}: {} of {}".format(company_name,i,num_units-1))
        device_id = uuid.uuid4()
        for j in range(1,32):
            end_time = time.mktime(datetime.datetime(2018,8,j,6,0,0,0).timetuple())
            end_point = get_random_point()
            placement_reason = 'maintenance_drop_off'
            while not day_over(end_time):
                if not boundary.contains(end_point):
                    # handles case where left outside boundary
                    # takes anywhere between 10 minutes and 2 hours for
                    # company to get it, placed randomly in service area
                    wait_time = random.uniform(10*60,2*60*60)
                    end_point = get_random_point()
                    availability_data.append([company_name,
                                              device_type,
                                              device_id,
                                              end_time,
                                              end_time + wait_time,
                                              'user_drop_off',
                                              False,
                                              'out_of_service_area_pick_up',
                                              None])
                    end_time = end_time + wait_time
                    placement_reason = 'out_of_service_area_drop_off'
                wait_time = random.uniform(0,wait_time_max(end_time))
                start_time = end_time + wait_time
                trip_id = uuid.uuid4()
                start_point = end_point
                trip_duration = numpy.random.chisquare(5)*1.2*60 # in seconds
                # we will assume scooters go about 4 m/s
                trip_distance = trip_duration*4                 
                # 20% penalty to account for roads - cannot take a straight path
                end_point = get_point_nearby(start_point,trip_distance*0.8)
                pickup_reason = 'user_pick_up'
                if day_over(start_time + trip_duration):
                    pickup_reason = 'maintenance_pick_up'
                availability_data.append([company_name,
                                          device_type,
                                          device_id,
                                          end_time,
                                          start_time,
                                          placement_reason,
                                          True,
                                          pickup_reason,
                                          None])
                end_time = start_time + trip_duration
                standard_cost = math.floor(trip_duration/60)/100
                actual_cost = (100 + (math.floor(trip_duration/60)-1)*15)/100
                parking_verification = url+"/images/" + random_string()
                placement_reason = 'user_drop_off'
                trip_data.append([company_name,
                                  device_type,
                                  trip_id,
                                  trip_duration,
                                  trip_distance,
                                  start_point,
                                  end_point,
                                  accuracy,
                                  None,
                                  None,
                                  device_id,
                                  start_time,
                                  end_time,
                                  parking_verification,
                                  standard_cost,
                                  actual_cost])
    trip_df = pd.DataFrame(trip_data,columns=trip_columns)
    availability_df = pd.DataFrame(availability_data, columns=availability_columns)
    return (trip_df, availability_df)

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
        data['data'].append(d)
    result = json.dumps(data,indent=4,separators=(',',': '))
    f = open(output_file,'w')
    f.write(result)

# convert availability data into json
def availability_convert(db,output_file):
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
        if d['allowed_placement']==1:
            d['allowed_placement'] = "true"
        else:
            d['allowed_placement'] = "false"
        d['device_id'] = str(d['device_id'])
        data['data'].append(d)
    result = json.dumps(data,indent=4,separators=(',',': '))
    f = open(output_file,'w')
    f.write(result)

print("Generating bat data.")
btrips,bavail = make_dataframes("Bat","scooter","bat.co",100)
print("Done.")
print("Generating Lemon data.")
ltrips,lavail = make_dataframes("Lemon","scooter","lemonbike.com",100)
print("Done.")

print("Writing Bat Trips JSON")
trip_convert(btrips,'bat_trips.json')
print("Done.")

print("Writing Lemon Trips JSON")
trip_convert(ltrips,'lemon_trips.json')
print("Done.")


print("Writing Bat Availability JSON")
availability_convert(bavail,'bat_availability.json')
print("Done.")

print("Writing Lemon Availability JSON")
availability_convert(lavail,'lemon_availability.json')
print("Done.")
