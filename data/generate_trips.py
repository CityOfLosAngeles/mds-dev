"""
This file will generate json files for each of our fake mobility providers
(FlipBird and Lemon) with trip data following the mobility data specifications
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

# generate district 10 boundary using gps coordinates
bounds = fiona.open('CouncilDistricts.shp')
original = pyproj.Proj(bounds.crs)
dest = pyproj.Proj(init='epsg:4326')
polygons = []
for poly in bounds[11]['geometry']['coordinates']: # get district 10
    polygon = [] # eventual converted polygon
    for x,y in poly:
        x_prime,y_prime = pyproj.transform(original,dest,x,y) # transform point
        p = (x_prime,y_prime)
        polygon.append(p)
    polygons.append(shapely.geometry.Polygon(polygon))
boundary = shapely.geometry.MultiPolygon(polygons) # our final boundary


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
        device_id = i+1
        print("Generating device {}:{}".format(company_name,device_id))
        for j in range(1,32):
            end_time = time.mktime(datetime.datetime(2018,8,j,6,0,0,0).timetuple())
            end_point = get_random_point()
            trip_id = 0
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
                trip_id += 1
                wait_time = random.uniform(0,wait_time_max(end_time))
                start_time = end_time + wait_time
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

fbtrips,fbavail = make_dataframes("FlipBird","scooter","flipbird.co",100)
ltrips,lavail = make_dataframes("Lemon","scooter","lemonbike.com",100)

fbtrips.to_csv('flipbird_trips.csv',encoding='utf-8',index=False)
fbavail.to_csv('flipbird_availability.csv',encoding='utf-8',index=False)
ltrips.to_csv('lemon_trips.csv',encoding='utf-8',index=False)
lavail.to_csv('lemon_availability.csv',encoding='utf-8',index=False)
