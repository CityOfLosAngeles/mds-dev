#!/usr/bin/env python3
"""
    Running this script generates a locally hosted Dash application with figures contructed from the transit SQL database.

    note:
    - file paths need to be changed for read_bounds and read_area
    - this script requires neccessary views: availability,
    - update Controls.py as needed with enumerations for company_name and device_type or vehicles_type 

    potential issues:
    - the Provider MDS spec has updated the field 'device_type' to 'vehicle_type'
    - the fake MDS data used to develop the dashboard still uses the field 'device_type' so all 'device_type' will 
    need to be changed 'vehicle_type' 

    
    to use:    python dash_app.py [username] [password] [database name]

    where [username] and [password] are for the sql server 

    Author: Hannah Ross

"""

import argparse
import numpy
import random
from copy import deepcopy
import os
import pickle
import copy
import datetime as dt
import pandas as pd
from flask import Flask
from flask_cors import CORS
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import calendar
import datetime
import plotly.plotly as py
import plotly.graph_objs as go
import sqlalchemy
import os
import pandas
import shapely.geometry
import pyproj
import psycopg2
import json
import requests
import ast
import shapely.wkt
import shapely.geometry
import pyproj
from ast import literal_eval
from mapboxgl.utils import *
from mapboxgl.viz import *
from shapely.geometry import shape,mapping, Point, Polygon, MultiPolygon
import shapely.ops
import dash_html_components as html
import fiona # must keep Fiona after shapely imports to avoid errors
from controls import COMPANIES,VEHICLES# controls allows for modularity with company names, plotly account settings, 

app = dash.Dash(__name__)
app.css.append_css({'external_url': 'https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css'})  # noqa: E501
server = app.server
CORS(server)

if 'DYNO' in os.environ:
    app.scripts.append_script({
                              'external_url': 'https://cdn.rawgit.com/chriddyp/ca0d8f02a1659981a0ea7f013a378bbd/raw/e79f3f789517deec58f41251f7dbb6bee72c44ab/plotly_ga.js'  # noqa: E501
                              })


################################################################### read in data from server
def connect(user,password,db,host='localhost',port=5432):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

# has commands to get data for fake data and commands for real data using real time now() parameters
def get_data(con):
    
    fake_trips_command = """
WITH time_view AS (
        WITH json_split AS (

                SELECT

                company_name,
                device_type,
                device_id,
                trip_duration,
                trip_distance,
                accuracy,
                route,
                json_array_elements(route->'features') AS loc,
                trip_id,
                parking_verification,
                standard_cost,
                actual_cost

                FROM

                trips
        )

        SELECT

        company_name,
        device_type,
        device_id,
        trip_duration,
        trip_distance,
        accuracy,
        route, 
        ((loc->'properties')->'timestamp') AS timestamp,
        (loc->'geometry')::text as location,
        trip_id,
        parking_verification,
        standard_cost,
        actual_cost

        FROM
        json_split
)

SELECT * FROM time_view WHERE to_timestamp( cast( cast(timestamp as text) as int ) ) > to_timestamp(1533416032) AND to_timestamp( cast( cast(timestamp as text) as int ) ) < to_timestamp(1533416032)+ INTERVAL \'7 DAY\'
"""

    real_trips_command = """
WITH time_view AS (
        WITH json_split AS (

                SELECT

                company_name,
                device_type,
                device_id,
                trip_duration,
                trip_distance,
                accuracy,
                route,
                json_array_elements(route->'features') AS loc,
                trip_id,
                parking_verification,
                standard_cost,
                actual_cost

                FROM

                trips
        )

        SELECT

        company_name,
        device_type,
        device_id,
        trip_duration,
        trip_distance,
        accuracy,
        route, 
        ((loc->'properties')->'timestamp') AS timestamp,
        (loc->'geometry')::text as location,
        trip_id,
        parking_verification,
        standard_cost,
        actual_cost

        FROM
        json_split
)

SELECT * FROM time_view WHERE to_timestamp( cast( cast(timestamp as text) as int ) ) > to_timestamp(1533416032) AND to_timestamp( cast( cast(timestamp as text) as int ) ) < to_timestamp(1533416032)+ INTERVAL \'7 DAY\'
"""

    # for FAKE DATA, use:
    trips_db = pandas.read_sql(fake_trips_command,con,index_col=None)
    status_change_db = pandas.read_sql('SELECT * FROM "status_change" WHERE to_timestamp(event_time) > to_timestamp(1533416032) AND to_timestamp(event_time) < to_timestamp(1533416032)+ INTERVAL \'7 DAY\'',con, index_col=None)

    # for REAL DATA,use:
    # trips_db = pandas.read_sql(real_trips_command,con,index_col=None) 
    # status_change_db = pandas.read_sql('SELECT * FROM "status_change" WHERE to_timestamp(event_time) > now() AND to_timestamp(event_time) < now() + INTERVAL \'7 DAY\'',con, index_col=None)
    
    return (trips_db,status_change_db)


print ("Loading in server data...")

parser = argparse.ArgumentParser()
parser.add_argument("user", type=str,
                    help="username to access postgresql database")
parser.add_argument("password", type=str,
                    help="password to access postgresql database")
parser.add_argument("database", type=str,
                    help="database name")
args = parser.parse_args()

# extract arguments to connect to server
user = args.user
password = args.password
db = args.database
con = connect(user,password,db)
tdb, scdb = get_data(con)

# for test generating, make shorter and quicker
print('NOW Shorting trips and status change...')
tdb=tdb.head(2000)
scdb = scdb.head(2000)


###################################################################  extract company names and the number of companies
companies = tdb['company_name'].unique()

###################################################################  read in council district boundaries
print("Processing council districts...")

# function to read in council district boundaries
def read_bounds(filename):
    bounds = fiona.open('/Users/newmobility/Desktop/mds-dev/data/shapefiles/' + filename)# fix file path issue
    return bounds

# read in council district boundaries
bounds= read_bounds('CouncilDistricts.shp')

all_bounds = [] # boundaries of all 15 council districts
for i in range(len(bounds)):
    original = pyproj.Proj(bounds.crs)
    dest = pyproj.Proj(init='epsg:4326')
    polygons = []
    polygons_list = []
    for poly in bounds[i]['geometry']['coordinates']: 
        polygon = [] # eventual converted polygon
        polygon_lists = []
        for x,y in poly:
            x_prime,y_prime = pyproj.transform(original,dest,x,y) # transform point
            p = (x_prime,y_prime)
            polygon.append(p)
            polygon_lists.append([x_prime,y_prime])
    polygons.append(shapely.geometry.Polygon(polygon))
    polygons_list.append(polygon_lists)
    boundary = shapely.geometry.MultiPolygon(polygons) 
    all_bounds.append(boundary)

# adjust order of bounds in shapefiles to align with council district number so that indice 0 is CD 1 and indice 14 is CD 15
order=[10, 4, 3, 6, 5, 2, 0, 13, 12, 11, 9, 1, 7, 8, 14]
all_bounds = [all_bounds[i] for i in order]

################################################################### compute a 16 by 16 array of trips from council district to council district
# array is constructed such that:
# a row sum is the total number of trips leaving a council district
# a column sum is the total number of trips entering a council district
# the last row is the sum of trips beginning out of bounds
# the last column is the sum of trips ending out of bounds (array indice [16][16] will be number of trips beginning and ending out of bounds )
def get_cd_array(tdb):
    co_end_points = []
    co_start_points = []
    for i in range(len(tdb)):
        cur_len = len(tdb['route'][i]['features'])
        co_end_points.append(tdb['route'][i]['features'][cur_len - 1]['geometry']['coordinates'] )
        co_start_points.append(tdb['route'][i]['features'][0]['geometry']['coordinates'])
    
    co_end_points = [shapely.geometry.Point(co_pt) for co_pt in co_end_points]
    co_start_points = [shapely.geometry.Point(co_pt) for co_pt in co_start_points]
    
    rows = []
    for i in range(16):
        r = [0 for i in range(16)]
        rows.append(r)
    
    for st,end in zip(co_start_points,co_end_points):
        start_tf=[b.contains(st) for b in all_bounds]
        end_tf = [b.contains(end) for b in all_bounds]
        
        try:
            start = start_tf.index(True)
        except:
            start = 15 # 15th row indice is for 16th starting out of bounds bin
            
        try:
            end = end_tf.index(True)
        except:
            end = 15 # 15th column indice is for 16th ending out of bounds bin
            
        rows[start][end] = rows[start][end]+1

    return rows
        

print("Calculating trips from council district to council district...")
cd_array = get_cd_array(tdb) # returns 16 by 16 array
cd_flatlist = [item for r in cd_array for item in r] # converts array into a flatlist of 225 values in order to be used for sankey flow plot

################################################################### preproccess trips for each council district
# begin comment 
print("Subsetting trips into dataframes per council district...")

# Function returns a data frame with all trip observations that start in a given council district
# tripsdb: a data frame of trips database
# cd_num: a specified council district
def trips_starting_in_cd(tripdb,cd_num):
    boundary = all_bounds[ cd_num - 1 ]
    co_start_points = [tripdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(tripdb))]
    co_pts = [shapely.geometry.Point(co_pt) for co_pt in co_start_points]
    bool_vec = [boundary.contains(p) for p in co_pts]   
    return tripdb.loc[bool_vec]

# cd_trips is a list of dataframes each storing the trips belonging to each council district
cd_trips = []
for i in range(1,16,1):
    cd_trips.append(trips_starting_in_cd(tdb,i))


################################################################### create status change map

print ("Generating status change map...")
token = 'pk.eyJ1IjoiaGFubmFocm9zczMzIiwiYSI6ImNqajR3aHcwYzFuNWcza3BnNzVoZzQzcHQifQ.eV_IJn3AdBE3n57rd2fhFA' # mapbox access token
 
# function creates a map of event_types
# scdb: a status change data frame from the status change database
def plot_status_changes(scdb):
    scdb_small = scdb
    start_points =[literal_eval(scdb_small['location'][i]) for i in scdb_small['location'].index] # extract starting location
    events = [scdb_small['event_type'][i] for i in range(len(scdb_small))] # extract corresponding event types for each starting location

    # create dataframes for startpoints and endpoints with lat and long coords to comply with mapbox plotting spec
    start_d = {'lat':[], 'lon':[],'event_type':[]}

    for start_p in start_points:
        start_lon,start_lat = start_p[0],start_p[1]
        start_d['lat'].append(start_lat)
        start_d['lon'].append(start_lon)

    for event_type in events:
        start_d['event_type'].append(event_type)

    startdb = pandas.DataFrame.from_dict(start_d)
    COLORS = dict(available= 'rgb(139,195,74)', unavailable = 'yellow', reserved= 'rgb(2,136,209)', removed='rgb(211,47,47)' )
    traces = []
    for ev_type, dff in startdb.groupby('event_type'):
        trace = dict(
                 type='scattermapbox',
                 lon=dff['lon'],
                 lat=dff['lat'],
                 name= ev_type,
                 text = ev_type,
                 )
        traces.append(trace)

    lay = go.Layout()
    lay['hovermode']='closest'
    lay['autosize'] = True
    lay['mapbox']['accesstoken']=token
    lay['mapbox']['zoom'] = 11
    lay['mapbox']['center']=dict(
                             lon=-118.33,
                             lat=34.017)
    lay['mapbox']['bearing']=0
    lay['mapbox']['style']="dark"
    lay['margin'] = dict(
        l=35,
        r=35,
        b=35,
        t=45
    )
    lay['title'] = 'Locations of Device Statuses'
    map_fig = go.Figure(data = traces,layout = lay)
    return map_fig

map_fig = plot_status_changes(scdb)

###################################################################  create bar chart for trips per council district

print("Generating plot of trips per council district...")

# function creates a double-bar chart (or more than double if more than 2 providers) for the number of trips taken in each council district per company. 
# tdb: a trips data frame 
def plot_trips_per_cd(tdb):
    traces = []
    for co in companies:
        co_dc_counts = []
        for df in cd_trips:
            co_df = df.loc[df['company_name'] == co]
            co_df = co_df.reset_index()
            co_dc_count = len(co_df)
            co_dc_counts.append(co_dc_count) # FOR REAL DATA
            co_dc_counts.append(random.randint(111000,119000)) # FOR FAKE DATA DEMO PURPOSES
        trace = go.Bar(
                    y = co_dc_counts, # values will depend on updating the above FAKE data append command with REAL data append command
                    x = [x for x in range(1,16,1)],
                    name = str(co)
                    )
        traces.append(trace)
    data = traces
    layout = go.Layout(
                       barmode = 'group',
                       title = "Trips Beginning in Each Council District",
                       yaxis = {"title": "Number of Trips"},
                       xaxis = {"title": "Council District"},
                       )            
    trips_per_cd_fig = go.Figure(data = data, layout = layout)
    return trips_per_cd_fig

trips_per_cd_fig = plot_trips_per_cd(tdb)

###################################################################  create pie chart of trips per company

print("Generating pie chart of trips per company...")

# function returns a pie chart of the percent of trips per company
# tripdb: a trips data frame from the trips database, may be a subset of exclusively bike or scooter trips.
def plot_trips_per_company(tripdb):
    newcompanies = tripdb['company_name'].unique()
    company_trip_pie_fig = {
            "data": [
        {
        "values": [],
        "labels": [co for co in newcompanies],
        "hoverinfo": "label + value",
        "type": "pie",
        "hole":0.5
        }, 
        ],
        "layout": {
        "title": "Trips Per Company"
         }
    } 
    for co in newcompanies:
        co_users = sum(tripdb['company_name'] == co)
        company_trip_pie_fig['data'][0]['values'].append(co_users)

    return company_trip_pie_fig

company_trip_pie_fig = plot_trips_per_company(tdb)


###################################################################  create sankey figure for equity zone flows

# only council district 10 is represented in fake data, so I have hard coded SF valley equity zone values for demo purposes

print("Generating equity zone sankey plot...")

# helper function to be used in processing shapefiels into multipolygons
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

# to process shapefiles into multipolygons
def read_area(file_name):
    area = fiona.open(file_name)
    original = pyproj.Proj(area.crs)
    dest = pyproj.Proj(init='epsg:4326')
    multi_polygon = []
    for a in area:
        a_type = a['geometry']['type']
        if a_type == "MultiPolygon":
            for poly in a['geometry']['coordinates']:
                multi_polygon.append(read_poly(poly, original, dest))
        elif a_type == "Polygon":
            multi_polygon.append(read_poly(a['geometry']['coordinates'], original, dest))
        return shapely.ops.cascaded_union(multi_polygon)
    
# read in equity zone boundaries
city_boundary = read_area('/Users/newmobility/Desktop/mds-dev/data/shapefiles/City_Boundary.shp')
sf_equity = read_area('/Users/newmobility/Desktop/mds-dev/data/shapefiles/San_Fernando_Valley.shp')
non_sf_equity = read_area('/Users/newmobility/Desktop/mds-dev/data/shapefiles/Non_San_Fernando.shp')

# fucntions returns a sankey diagram for traffic flows between the 3 equity zones  
# tripsdb: a trips data frame (may be fed company specific trips for company specific equity measures )
def plot_equity_sankey(tripdb):
    co_trip_starts = []
    co_trip_ends = []
    
    for i in range(len(tripdb)):
        co_trip_starts.append(tripdb['route'][i]['features'][0]['geometry']['coordinates'])
        co_trip_ends.append(tripdb['route'][i]['features'][1]['geometry']['coordinates'])
    

    # if length is > 1 do not label title with company
    val_to_val = 0
    val_to_nonval = 0
    val_to_city = 0
    nonval_to_nonval = 0
    nonval_to_val = 0
    nonval_to_city = 0
    city_to_city = 3000
    city_to_val = 20000
    city_to_nonval = 120000

    '''
    # comment out -- code works, but takes too long for data that does not cover all 3 zones anyways
    for i in range(len(tdb)):
        startpt = shapely.geometry.Point(co_trip_starts[i])
        endpt = shapely.geometry.Point(co_trip_ends[i])
        if (sf_equity.contains(startpt)):
            if non_sf_equity.contains(endpt):
                val_to_nonval=val_to_nonval + 1
            elif sf_equity.contains(endpt):
                val_to_val = val_to_val + 1
            else:
                val_to_city = val_to_city + 1
        elif (non_sf_equity.contains(startpt)):
            if non_sf_equity.contains(endpt):
                nonval_to_nonval= nonval_to_nonval + 1
            elif sf_equity.contains(endpt):
                nonval_to_val = nonval_to_val + 1
            else:
                nonval_to_city = nonval_to_city + 1
        elif  (city_boundary .contains(startpt)):
            if non_sf_equity.contains(endpt):
                city_to_nonval= city_to_nonval + 1
            elif sf_equity.contains(endpt):
                city_to_val = city_to_val + 1
            else:
                city_to_city = city_to_city + 1
        else:
            None   
    '''

    # hard coded values to compensate for lack of valley representation in fake data
    val_to_val = 100000
    val_to_nonval = 20000
    val_to_city = 32000
    nonval_to_val = 20000
    nonval_to_nonval = 300000
    nonval_to_city = 650000
    city_to_val = 12000

    data = dict(
           type='sankey',
            node = dict(
                        pad = 15,
                        thickness = 30,
                        line = dict(
                                    color = "black",
                                    width = 0
                                    ),
                        label = ["San Fernando Valley Equity Zone", "Non San Fernando Valley Equity Zone", "Non-Equity City Zone","San Fernando Valley Equity Zone", "Non San Fernando Valley Equity Zone", "Non-Equity City Zone"],
                        color = ["#4994CE", "#ff853d", "#80b280", "#4994CE", "#ff853d", "#80b280"]
                        ),
            link = dict(
                        source = [0,0,0,1,1,1,2,2,2],
                        target = [3,4,5,4,3,5,5,3,4],
                        value = [val_to_val, val_to_nonval, val_to_city,
                                 nonval_to_nonval, nonval_to_val, nonval_to_city,
                                 city_to_city, city_to_val, city_to_nonval],
                        color = [ "#a6cbe7", "#a6cbe7", "#a6cbe7","#ffc2a3", "#ffc2a3", "#ffc2a3", "#b2d1b2", "#b2d1b2", "#b2d1b2"]
                        )
            )

    # if only 1 company given, the function is plotting a company specific subset and should label it as that company's equity breakdown
    if len(tripdb['company_name'].unique()) is 1:
        co = tripdb['company_name'].unique()[0] # co is company label used in title of plot
    else: # more than 1 company is represented in dataframe
        co = "" # it is an aggregate plot, so should not specificy a certain provider in title

    layout =  dict(
                   title = "{} Traffic Between Equity Zones".format(co), # update title with given company 
                   font = dict( 
                               size = 12
                               ),
                   updatemenus = [
                                 dict(
                                      y = 0.6,
                                      buttons = [
                                               dict(
                                                    label = 'Horizontal',
                                                    method = 'restyle',
                                                    args = ['orientation', 'h']
                                                    ),
                                               dict(
                                                    label = 'Vertical',
                                                    method = 'restyle',
                                                    args = ['orientation', 'v']
                                                    )
                                               ]
                                      
                                      )
                                 ]
                   )

    sankey_fig = go.Figure(data = [data], layout = layout)
    return sankey_fig

sankey_fig = plot_equity_sankey(tdb) 

################################################################### create sankey plot for council district flows

# define colors for council district flows
colors = ['#EF431A',
 '#9F359D',
 '#34325B',
 '#84C4E0',
 '#FB606D',
 '#E1F710',
 '#7C03F1',
 '#99DC11',
 '#BAB7F7',
 '#18B994',
 '#D9804B',
 '#0C17CC',
 '#FA9D6D',
 '#557223',
 '#99FFEB',
 '#746FB1']

# order colors for sankey diagram flows. 
# c: link colors
# colors: node colors

c = [] # link colors
for i in range(15):
    temp = colors[i]
    for i in range(15):
        c.append(temp)

# function returns a council district sankey diagram. used only in the callback function for a cd selector with default set to cd 10.
# cd_flatlist: flat list with  225 values from the 16x16 array of trips from cd to cd
def plot_cd_sankey(cd_flatlist):
    data = dict(
        type='sankey',
        width = 1118,
        height = 1118,
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(
                color = "black",
                width = 0
                ),
            label = ["CD1", "CD2","CD3","CD4", "CD5","CD6","CD7","CD8","CD9","CD10","CD11","CD12","CD13","CD14","CD15","Outside L.A.","CD1", "CD2","CD3","CD4", "CD5","CD6","CD7","CD8","CD9","CD10","CD11","CD12","CD13","CD14","CD15","Outside L.A."],
            color = colors + colors,
        ),
        link = dict(
            source = [i for i in range(16) for j in range(16)],
            target = [i+16 for j in range(16) for i in range(16)], #endinds,
            value = cd_flatlist, # convert array into a flat list. array is 15 by 15 
            color = c
               )
        )

    layout =  dict(
        title = "Traffic Between Council Districts",
        font = dict(
                    size = 10
                    )
    )
    fig = dict(data=[data], layout=layout)
    return fig
    

#cd_sankey = plot_cd_sankey(cd_flatlist)

################################################################### create bar chart for trips per hour


# helper function to return =dataframe with trips in falling within a specified interval
# firstday: datetime time stamps 
# lastday: datetime time stamps
# pd_df: trips pandas dataframe
def obs_in_days(firstday,lastday,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    bool_vec = [((datetime.datetime.utcfromtimestamp(d) >= firstday) & (datetime.datetime.utcfromtimestamp(d) <= lastday)) for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

# helper function used for plotting trips per hour, returns am-pm times from military time
# hour: integer between 0 and 23
def to_twelve_hour(hour):
    if hour > 12:
        new = hour - 12
        return str(new) + 'PM'
    elif hour == 12:
        return str(hour) + 'PM'
    elif hour == 0:
        return str(12) + 'AM'
    else:
        return str(hour) + 'AM'

# function returns pbar lot for the number of trips taken per hour 
# tripdb: trips data frame
def plot_trips_per_hour(tripdb):
    start_times = [tripdb['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(tripdb))]
    hour_vec=[datetime.datetime.fromtimestamp(d).hour for d in start_times]
    hour_vec_ampm = [to_twelve_hour(t) for t in hour_vec]
    ampm_hours = ['12AM', '1AM','2AM','3AM','4AM','5AM', '6AM','7AM','8AM','9AM','10AM', '11AM','12PM','1PM','2PM','3PM','4PM','5PM','6PM','7PM','8PM','9PM','10PM','11PM']
    yvals = []
    for i in range(len(ampm_hours)):
        time = ampm_hours[i]
        yvals.append(sum([(hour_vec_ampm[j] == time) for j in range(len(hour_vec_ampm))]))
    
    trace=go.Bar(x = ampm_hours,y = yvals)
    data=[trace]
    layout=go.Layout(title = 'Trips Per Hour',barmode = 'group',bargroupgap = 0.5)
    layout.yaxis = dict(title = "Number of Trips")
    layout.xaxis = {
    'type': 'date',
    'tickformat': '%H:%M',
    }
    layout.xaxis = dict(title = "Hour of Day",tickmode = 'linear')
    hours_fig = go.Figure(data = data,layout = layout)
    return hours_fig


# can filter trips database using obs_in functions for date window specification
#tdb_filtered = obs_in_days(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 10, 8, 33, 13),tdb)
print("NOT Generating trips per hour figure...")
#hours_plot_fig = plot_trips_per_hour(tdb)

###################################################################  create plot of 24 hour availabilities per device ratios

# function reads in the availability view from sql server
def get_availability(con):
    availability_db = pandas.read_sql('SELECT * FROM "availability"',con,index_col=None)
    return availability_db

# read in the availability view
print("Reading in availability view")
availdb = get_availability(con)

print('NOW shorting avail db')
availdb = availdb.head(1000) 

# helper function for availability ratio plot that returns the number of availability periods in a given hour from availability view
def avail_dev_in_hour(hour,pd_df): 
    start_time = [time for time in pd_df['start_time']]
    end_time = [time for time in pd_df['end_time']]
    hr = hour
    count = 0
    for i in range(len(end_time)): # count all observations falling within the specified hour interval
        t_s = start_time[i]
        t_e = end_time[i]
        if numpy.isnan(t_e): # no end time
            break
        if numpy.isnan(t_s): # no start time
            break
        if datetime.datetime.utcfromtimestamp(t_s).hour==hr: # starting hour is during interval
            count = count + 1
        elif datetime.datetime.utcfromtimestamp(t_s).hour<hr and datetime.datetime.utcfromtimestamp(t_e).hour>hr: # starting hour before interval ends after interval
            count = count + 1
        elif datetime.datetime.utcfromtimestamp(t_e).hour==hr: # ending hour is in interval
            count = count + 1
        else:
            None
    return count

print("Generating availability ratio plot...")

# returns an availability per dev ratio plot comparing all provider to a standard modular:
def plot_availability_ratios(availdb):
    traces = [] # to store ratio traces for each company
    for co in availdb['company_name'].unique():
        # extract availability view rows
        co_avail = availdb.loc[availdb['company_name'] == co]
        num_avail = len(co_avail['device_id'].unique())
        # compute unique device count for deployed vehicles per company
        tot_dev_per_24hour = [num_avail] * 24
        tot_dev_avail_per_24hour = []
        for i in range(0,24,1):
            coavail = avail_dev_in_hour(i,co_avail)
            tot_dev_avail_per_24hour.append(coavail)
        # ensure not dividing by 0 in ratio of avail dev / tot dev
        co_zeros = []
        for i in range(len(tot_dev_avail_per_24hour)):
            if tot_dev_per_24hour[i] == 0:
                co_zeros.append(i) # track loc of zeros

        for i in co_zeros:
            tot_dev_per_24hour[i] = 0.01

        co_avail_ratio = [float( tot_dev_avail_per_24hour[i] ) / tot_dev_per_24hour[i] for i in range(24)]# num avail per num devices
        trace = go.Scatter(
            x = [x for x in range(0,24,1)],
            y = co_avail_ratio,
            name = '{} Availability Ratio'.format(co)
            )
        traces.append(trace) # add a trace for each company 

    # define required standard trace for companies to be compared to
    trace1 = go.Scatter(
    x = [ x for x in range(0,24,1) ],
    y = [2] * 24, # for real data, can adjust this '[2]' to be the required standard ratio of availability per device per hour
    mode = 'lines',
    name = 'Required Standard',
    line = dict(
        color = 'red',
        width = 4,
        dash = 'dash')
    )
    traces.append(trace1)


    data = traces
    layout = dict(title = 'Availabilities Per Device',
              xaxis = dict(title = 'Hour of Day'),
              yaxis = dict(title = 'Availabilities Per Device'),
              )
    avail_per_dev_fig = go.Figure(data = data, layout = layout)

    return avail_per_dev_fig
    
avail_per_dev_fig = plot_availability_ratios(availdb)
            
'''
# extract both companies' availability view rows
lemon_avail = availdb.loc[availdb['company_name'] == 'Lemon']
bat_avail = availdb.loc[availdb['company_name'] == 'Bat']

# compute the unique devices for count of deployed devices per company
num_bat = len(bat_avail['device_id'].unique())
num_lemon = len(lemon_avail['device_id'].unique())

tot_bat_dev_per_24hour = [num_bat] * 24
tot_lemon_dev_per_24hour = [num_lemon] * 24

# compute the number of available windows during each of 24 hours ** counting overlapping hours too
tot_bat_avail_per_24hour = []
tot_lemon_avail_per_24hour = []

for i in range(0,24,1):
    batavail = avail_dev_in_hour(i,bat_avail)
    lemonavail = avail_dev_in_hour(i,lemon_avail)
    tot_bat_avail_per_24hour.append(batavail)
    tot_lemon_avail_per_24hour.append(lemonavail)

# adjust zeros for ratio calculation 
bat_zeros = []
lemon_zeros = []
for i in range(len(tot_bat_avail_per_24hour)):#,tot_lemon_avail_per_24hour):
    if tot_bat_dev_per_24hour[i] == 0: # record indices with zeros to allow for dividing by 0 for ratio calculations
        bat_zeros.append(i)
    if tot_lemon_dev_per_24hour[i] == 0:
        lemon_zeros.append(i)
               
for i in bat_zeros:
    tot_bat_dev_per_24hour[i] = 0.01
for i in lemon_zeros:
    tot_lemon_dev_per_24hour[i] = 0.01

# compute number of availability windows per device: # availibility / total devices
lemon_avail_ratio = [float( tot_lemon_avail_per_24hour[i] ) / tot_lemon_dev_per_24hour[i] for i in range(24)]#num avail  per num devices
bat_avail_ratio = [float( tot_bat_avail_per_24hour[i] )  / tot_bat_dev_per_24hour[i] for i in range(24)]# num avail  per num devices

trace = go.Scatter(
    x = [x for x in range(0,24,1)],
    y = bat_avail_ratio,
    name = 'Bat Availability Ratio'
)

trace0 = go.Scatter(
    x = [x for x in range(0,24,1)],
    y = lemon_avail_ratio,
    mode = 'lines',
    name = 'Lemon Availability Ratio'   
)

trace1 = go.Scatter(
    x = [ x for x in range(0,24,1) ],
    y = [2] * 24, # adjust this '[2]' to be the required standard ratio of availability per device per hour
    mode = 'lines',
    name = 'Required Standard',
    line = dict(
        color = 'red',
        width = 4,
        dash = 'dash')
)

data = [trace,trace0,trace1]
layout = dict(title = 'Availabilities Per Device',
              xaxis = dict(title = 'Hour of Day'),
              yaxis = dict(title = 'Availabilities Per Device'),
              )
avail_per_dev_fig = go.Figure(data = data, layout = layout)
'''


# end comment out block
import plotly.graph_objs as go
import plotly.plotly as py

# function returns double bar chart of the numer of trips starting and ending in each council district
# tdb: trips dataframs
def plot_cd_start_and_ends(tdb):
    co_end_points = []
    co_start_points = []
    '''
    for i in range(len(tdb)):
        cur_len = len(tdb['route'][i]['features'])
        co_end_points.append(tdb['route'][i]['features'][cur_len - 1]['geometry']['coordinates'] )
        co_start_points.append(tdb['route'][i]['features'][0]['geometry']['coordinates'])
    # count starts in each cd
    co_end_points = [shapely.geometry.Point(co_pt) for co_pt in co_end_points]
    co_start_points = [shapely.geometry.Point(co_pt) for co_pt in co_start_points]
    
    total_cd_starts =[]
    total_cd_ends = []
    
    for i in range(len(all_bounds)):
        boundary = all_bounds[i]
        start_cd_count = 0
        end_cd_count = 0
        for st,end in zip(co_start_points,co_end_points):
            #pt = shapely.geometry.Point(co_pt)
            if boundary.contains(st):
                start_cd_count = start_cd_count + 1
            if boundary.contains(end):
                end_cd_count = end_cd_count + 1
        total_cd_starts.append(start_cd_count)
        total_cd_ends.append(end_cd_count)
    '''
    # use 16 x 16 cd_array's row sum and column sum properties to calculate trips entering and leaving each cd
    def num_trips_leaving_cd(cdnum):
        sum = 0
        for i in range(15):
            sum = sum + cd_array[cdnum-1][i]
        return sum

    def num_trips_entering_cd(cdnum):
        sum = 0
        for i in range(15):
            sum = sum + cd_array[i][cdnum-1]
        return sum

    total_cd_starts = [num_trips_leaving_cd(i) for i in range(1,16)]
    total_cd_ends = [num_trips_entering_cd(i) for i in range(1,16)]
    
    trace = go.Bar(
                    y = total_cd_starts,
                    x = [x for x in range(1,16,1)],
                    name="trip starts",
                     marker=dict(
                        color='rgba(50, 171, 96, 0.7)',
                        line=dict(
                                color='rgba(50, 171, 96, 1.0)',
                                width=2,
                                ) 
                            )        
                 )

    trace2 = go.Bar(y= total_cd_ends, x = [x for x in range(1,16,1)],name = "trip ends",
                marker=dict(
                    color='rgba(219, 64, 82, 0.7)',
                    line=dict(
                        color='rgba(219, 64, 82, 1.0)',
                        width=2,
                            )
                        )
                    )
    data= [trace,trace2]
    layout = go.Layout(
                       barmode='group',
                       title="Number of Trips Starting and Ending Per Council District",
                       yaxis={"title":"Counts"},
                       xaxis={"title":"Council District"},
                       )            
    trip_starts_v_ends_fig = go.Figure(data=data, layout=layout)
    return trip_starts_v_ends_fig

trip_starts_v_ends_fig = plot_cd_start_and_ends(tdb)

####################################################### plot trips per day of week

# helper function returns trip database observations that occur  within a period of 2 specified days  (days are datetime objects)
def obs_in_days(firstday,lastday,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    bool_vec = [((datetime.datetime.utcfromtimestamp(d) >=firstday) & (datetime.datetime.utcfromtimestamp(d)<= lastday)) for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

# helper function extracts the days of each trip for plotting trips taken per day of week
def get_days_of_trips(tripsdf):
    start_time = [tripsdf['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(tripsdf))]
    return [calendar.day_name[datetime.datetime.utcfromtimestamp(x).weekday()] for x in start_time]

# helper function counts the frequency of each day given a list of days, to be used for plotting trips per day of week
def count_days(day,dayvec):
    vec=[dayvec[i]==day for i in range(len(dayvec))]
    return sum(vec)

# function returns a double bar plot for the number of trips taken per day of week for each company *can select  legend to view one company at a time
###init_trips_df = obs_in_days(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 10, 8, 33, 13), tdb)#
def plot_trips_per_weekdays(trips_df ):
    
    traces=[]
    # add a trace counting trips per day of week for each company
    # companies is the list of companies in the initial comprehensive trips data base
    for co in companies:
        df = trips_df.loc[trips_df['company_name'] ==  co].reset_index()
        
        trips_by_day = get_days_of_trips(df)

        mon_count = count_days('Monday',trips_by_day)
        tues_count = count_days('Tuesday',trips_by_day)
        wed_count  = count_days('Wednesday',trips_by_day)
        thurs_count = count_days('Thursday',trips_by_day)
        fri_count  = count_days('Friday',trips_by_day)
        sat_count  = count_days('Saturday',trips_by_day)
        sun_count = count_days('Sunday',trips_by_day)
        
        trace = go.Bar(
                       y=[mon_count,tues_count,wed_count,thurs_count,fri_count,sat_count,sun_count ],
                       x= [x for x in calendar.day_name],
                       name= co
                       )
        traces.append(trace)
    
    data=traces
    layout = go.Layout(
                       barmode='group',
                       title="Trips Per Day of Week",
                       yaxis={"title":"Number of Trips"}
                       )
        
    double_bar_fig = go.Figure(data=data, layout=layout)
                       
    return double_bar_fig

#trips_per_weekday_fig = plot_trips_per_weekdays(tdb )

################################################################### Plot drop offs by provider
# show map of provider drop offs
print("Generating map of provider drop offs...")
token = 'pk.eyJ1IjoiaGFubmFocm9zczMzIiwiYSI6ImNqajR3aHcwYzFuNWcza3BnNzVoZzQzcHQifQ.eV_IJn3AdBE3n57rd2fhFA' # mapbox token
# co is an optional parameter to see provider specific drop offs

# function returns a plot of device Drop Offs ( default plot is for plotting all companies' drop offs, but can plot 1 specified company)
def plot_dropoffs(scdb,co = None):
    #scdb_small = scdb.head(200) # for demo purposes
    scdb_small = scdb
    if co != None:
        bool_vec = [scdb_small['company_name'][i] in co for i in range(len(scdb_small))]
        scdb_small = scdb_small.loc[bool_vec].reset_index()

    avail_boolvec = [scdb_small['event_type'][i]=='available' for i in range(len(scdb_small))]
    avail_scdb = scdb_small.loc[avail_boolvec].reset_index() # get all avail event types
    points =[literal_eval(avail_scdb['location'][i]) for i in avail_scdb['location'].index]
    reasons = [avail_scdb['reason'][i] for i in range(len(avail_scdb))] # extract reaons for the avails
 
    # create dataframes for startpoints and endpoints with lat and long coords
    df = {'lat':[], 'lon':[],'reason':[]} # maybe add a company field?

    for p in points:
        lon,lat = p[0],p[1]
        df['lat'].append(lat)
        df['lon'].append(lon)

    for r in reasons:
        df['reason'].append(r)

    startdb = pandas.DataFrame.from_dict(df)
    COLORS = dict(out_of_service_area_drop_off = 'green',service_start = 'RGB(255,69,0)', user_drop_off = 'RGB(131,111,255)', rebalance_drop_off = 'rgb(2,136,209)', maintenance_drop_off ='rgb(211,47,47)' )
    traces = []
    
    for reason, dff in startdb.groupby('reason'):
        if reason == 'service_start': 
            reason_text = "Initial Service Dropoff"

            trace1 = dict(
                 type='scattermapbox',
                 lon=dff['lon'],
                 lat=dff['lat'],
                 name= reason_text,
                 text = reason_text,
                 marker = dict(
                             size=11,
                             opacity=1,
                             color=COLORS[reason],
                             ),
                 )
            traces.append(trace1)
        if reason == 'user_drop_off':
            reason_text = "Constituent Device Drop Off"
            trace2 = dict(
                 type='scattermapbox',
                 lon=dff['lon'],
                 lat=dff['lat'],
                 name= reason_text,
                 text = reason_text,
                 marker = dict(
                            color=COLORS[reason]
                             ),
                 )
            traces.append(trace2) 
       
    if co == None:
        co_text = ""
    else:
        co_text = co+""
    lay = go.Layout()
    lay['hovermode']='closest'
    lay['autosize'] = True
    lay['mapbox']['accesstoken']=token
    lay['mapbox']['zoom'] = 11
    lay['mapbox']['center']=dict(
                             lon=-118.33,
                             lat=34.017)
    lay['mapbox']['bearing']=0
    lay['mapbox']['style']="dark"
    lay['margin'] = dict(
        l=35,
        r=35,
        b=35,
        t=45
    )
    lay['title'] = 'Location of {}Drop Offs'.format(co_text) # if a company is specified, add company name if do company
    map_fig = go.Figure(data = traces,layout = lay)
    return map_fig

dropoffs_fig = plot_dropoffs(scdb) # indice 0 because if shorting then only 1 provider in head

print("the length of scdb at time of the drop off fig is ",len(scdb)) # for debugging


#################################################################### create bar chart for neighborhoods in a cd
# read in neighborhoods bounds
print("reading in neighborhoods files ...")
area = fiona.open("/Users/newmobility/Desktop/mds-dev/data/shapefiles/la_neighborhoods.shp")
original = pyproj.Proj(area.crs, preserve_units=True)
dest = pyproj.Proj(init='epsg:4326')
hood_dict={}
hood_dict['hoods']=[]
hood_dict['names'] = []
for a in area:
    hood_dict['names'].append(a['properties']['COMTY_NAME'])
    neighborhood = read_poly(a['geometry']['coordinates'],original,dest)
    hood_dict['hoods'].append(neighborhood)

# create a dictionary to use for sankey and bar charts
hoods_in_cd = {'cd':[],'hood_names':[],'hood_bounds':[]} # use this ot make sankeys foe hoods in each cd
for i in range(15):
    curcd_hood_names = []
    curcd_hood_bounds = []
    for j in range(len(hood_dict['hoods'])):
        if hood_dict['hoods'][j].intersects(all_bounds[i]):
            curcd_hood_names.append(hood_dict['names'][j])
            curcd_hood_bounds.append(hood_dict['hoods'][j])
    hoods_in_cd['hood_names'].append(curcd_hood_names)
    hoods_in_cd['hood_bounds'].append(curcd_hood_bounds)

# returns an array where the width and height is the number of neighborhoods in a given council disrict, 
# and the values are the trips between a given cd's neighborhoods
# tdb: trips data frame
# cdnum_for_hoods: the INDICE of the council district that neighborhoods are in (ie: council district 4's num would be 3)
def get_hoods_array(tdb,cdnum_for_hoods):
    co_end_points = []
    co_start_points = []
    cur_tdb = cd_trips[cdnum_for_hoods] # use only tripsdb for trips beginning in that council district

    # extract all points that start in the cd so that if a point is not in a cd's neighborhood bin, it is not because the point belongs to another cd 
    for i in range(len(cur_tdb)):
        cur_len = len(cur_tdb['route'][i]['features'])
        co_end_points.append(cur_tdb['route'][i]['features'][cur_len - 1]['geometry']['coordinates'] )
        co_start_points.append(cur_tdb['route'][i]['features'][0]['geometry']['coordinates'])
    
    co_end_points = [shapely.geometry.Point(co_pt) for co_pt in co_end_points]
    co_start_points = [shapely.geometry.Point(co_pt) for co_pt in co_start_points]
    
    rows = []
    for i in range(len(hoods_in_cd['hood_bounds'][cdnum_for_hoods])+1 ):
        r = [0 for i in range(len(hoods_in_cd['hood_bounds'][cdnum_for_hoods]) +1)]
        rows.append(r)
    
    for st,end in zip(co_start_points,co_end_points):
        start_tf=[b.contains(st) for b in hoods_in_cd['hood_bounds'][cdnum_for_hoods]] # cd 9 hoods
        end_tf = [b.contains(end) for b in hoods_in_cd['hood_bounds'][cdnum_for_hoods]] # cd 9 hoods
        
        try:
            start = start_tf.index(True)
        except:
            start = len(hoods_in_cd['hood_bounds'][cdnum_for_hoods]) # last row indice is for 16th starting out of bounds bin
            
        try:
            end = end_tf.index(True)
        except:
            end = len(hoods_in_cd['hood_bounds'][cdnum_for_hoods])  # last column indice is for 16th ending out of bounds bin
            
        rows[start][end] = rows[start][end]+1

    return rows
        
print("Computing neighborhoods arrays for each council district...")

cd_hoods_arrays =[] # to store all of the nieghborhood arrays for each cd. it is an array of length 15 holding multiple dynamicaly sized arrays for each cd.
for i in range(15): # get array for the niehgborhoods of all 15 cds
    cur_cd_hood_array = get_hoods_array(tdb,i)
    cd_hoods_arrays.append(cur_cd_hood_array)

# to generate all colors necessary for all sankey flows and nodes
r = lambda: random.randint(0,255)
colors=['#%02X%02X%02X' % (r(),r(),r()) for i in range(50000)]
'''
c = []
for i in range(len(hoods_in_cd['hood_bounds'][9])+1):
    temp = colors[i]
    for i in range(len(hoods_in_cd['hood_bounds'][9])+1):
        c.append(temp)
def plot_cd_hood_sankey(cd_flatlist):
    data = dict(
        type='sankey',
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(
                color = "black",
                width = 0
                ),
            label = hoods_in_cd['hood_names'][9] + ["outside LA"] + hoods_in_cd['hood_names'][9] + ["outside LA"],
            #label = ["CD1", "CD2","CD3","CD4", "CD5","CD6","CD7","CD8","CD9","CD10","CD11","CD12","CD13","CD14","CD15","Outside L.A.","CD1", "CD2","CD3","CD4", "CD5","CD6","CD7","CD8","CD9","CD10","CD11","CD12","CD13","CD14","CD15","Outside L.A."],
            color = colors[:39] + colors[:39],
        ),
        link = dict(
            source = [i for i in range(len(hoods_in_cd['hood_bounds'][9])+1) for j in range(len(hoods_in_cd['hood_bounds'][9])+1)],
            target = [i+len(hoods_in_cd['hood_bounds'][9])+1 for j in range(len(hoods_in_cd['hood_bounds'][9])+1) for i in range(len(hoods_in_cd['hood_bounds'][9])+1)], #endinds,
            value = cd_flatlist, # convert array into a flat list. array is 15 by 15 
            color = c
               )
        )

    layout =  dict(
        title = "Traffic Between Council District 10 Neighborhoods",
        font = dict(
                    size = 10
                    )
    )
    fig = dict(data=[data], layout=layout)
    return fig
    

cd_sankey = plot_cd_hood_sankey(cd_10_hoods_flatlist)
'''



###################################################################  Create app layout

# use data imported from Controls.py to define drop down options for company/mobility provider and the device type.
vehicle_options = [{'label': str(VEHICLES[mode].capitalize()), 'value': str(mode)}
                                        for mode in VEHICLES]
vehicle_options.insert(0,{'label':'All','value':None})

company_options = [{'label': str(COMPANIES[co].capitalize()), 'value': str(co)}
                                        for co in COMPANIES]
company_options.insert(0,{'label':'All','value':None})                                  
                    
co_opt_list = [] #options = co_opt_list
for co in companies:
    d = {}
    d['label'] = co
    d['value'] = co
    co_opt_list.append(d)
#provider_opt_list = []

times = [datetime.datetime.utcfromtimestamp(scdb['event_time'][i]) for i in range(len(scdb))]
sorted_times = sorted(times)
start_week = sorted_times[0].strftime(' %B %d, %Y')
end_week = sorted_times[len(scdb)-1].strftime('  -  %B %d, %Y')
cur_week = start_week + end_week # label of the dashboard's currrent week

app.layout = html.Div(
                      [
                       html.Div(
                                [
                                 html.H1(
                                         'Dockless Dashboard | Weekly Overview',
                                         className =  'eight columns',
                                         ),
                                 html.Img(
                                          src = "https://static1.squarespace.com/static/5952a8abbf629aef69513d41/t/595565dd4f14bc185894d47d/1498768870821/New+LADOT+Logo.png",
                                          className = 'one columns',
                                          style = {
                                          'height': '100',
                                          'width': '225',
                                          'float': 'right',
                                          'position': 'relative',
                                          },
                                        ),
                                 ],
                                className = 'row'
                                ),
                                # begin adding text to top of app
                                html.Div(
            [
                html.H5(
                    cur_week,
                    id='top_text',
                    className='eight columns'
                ),
                html.Br(),
                html.Br(),   
            ],
            className='row'
        ),
        # end adding text to top of app

        # begin adding radio select that updates provider_text and mode options
        html.Div([
                                html.Div([
                                            html.Label('See traffic leaving a Council District'),
                                            dcc.Dropdown(id = 'cd_start',
                                             
                                    options = [
                                    {'label': 'All Districts', 'value': None},
                                    {'label': 'Council District 1', 'value': 1},
                                    {'label': 'Council District 2', 'value': 2},
                                    {'label': 'Council District 3', 'value': 3},
                                    {'label': 'Council District 4', 'value': 4},
                                    {'label': 'Council District 5', 'value': 5},
                                    {'label': 'Council District 6', 'value': 6},
                                    {'label': 'Council District 7', 'value': 7},
                                    {'label': 'Council District 8', 'value': 8},
                                    {'label': 'Council District 9', 'value': 9},
                                    {'label': 'Council District 10', 'value': 10},
                                    {'label': 'Council District 11', 'value': 11},
                                    {'label': 'Council District 12', 'value': 12},
                                    {'label': 'Council District 13', 'value': 13},
                                    {'label': 'Council District 14', 'value': 14},
                                    {'label': 'Council District 15', 'value': 15},  
                                    {'label': 'Outside L.A.', 'value': 16}, 
                                    ],
                                    value = 10,
                                    
                                    ),
                                html.Label(''),
                                            dcc.Checklist(
                                                id='lock_selector', # checkbox used to clear out-flowing vs in-flowing user sankey selections
                                                options=[
                                                    {'label': 'double click to clear settings', 'value': 'clear'}
                                                ],
                                        values=[],
                                    ),
                                            html.Label('See traffic entering a Council District'),
                                            dcc.Dropdown(id = 'cd_end',
                                             
                                    options = [
                                    {'label': 'All Districts', 'value': None},
                                    {'label': 'Council District 1', 'value': 1},
                                    {'label': 'Council District 2', 'value': 2},
                                    {'label': 'Council District 3', 'value': 3},
                                    {'label': 'Council District 4', 'value': 4},
                                    {'label': 'Council District 5', 'value': 5},
                                    {'label': 'Council District 6', 'value': 6},
                                    {'label': 'Council District 7', 'value': 7},
                                    {'label': 'Council District 8', 'value': 8},
                                    {'label': 'Council District 9', 'value': 9},
                                    {'label': 'Council District 10', 'value': 10},
                                    {'label': 'Council District 11', 'value': 11},
                                    {'label': 'Council District 12', 'value': 12},
                                    {'label': 'Council District 13', 'value': 13},
                                    {'label': 'Council District 14', 'value': 14},
                                    {'label': 'Council District 15', 'value': 15}, 
                                    {'label': 'Outside L.A.', 'value': 16},  
                                    ],
                                    value = None,
                                    ),

                                 ],
                                 className = 'eight columns'
                                 ),

        html.Div(
                    [
                        html.P('Filter by mobility provider:'),
                        dcc.RadioItems(
                            id='provider_selector',
                            options = company_options,
                            value=None,
                            labelStyle={'display': 'inline-block'},
                            style={'text-align': 'center'}
                        ),
                        html.Br(),
                        html.P('Filter by vehicle type:'),
                        dcc.RadioItems(
                            id='mode_selector',
                            options = vehicle_options,
                            value=None,
                            labelStyle={'display': 'inline-block'},
                            style={'text-align': 'center'}
                        ),
                        #
                        #
                    ],
                    className='four columns'
                    
                ),
        ],
        className = 'row'
        ),
        # end adding radio select
        # begin  first row
html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(id='cd_sankey')
                    ],
                    className='eight columns',
                    style={'margin-top': '20'}
                ),
                html.Div(
                    [
                        dcc.Graph(id='company_trips_pie_fig', # this was same name as company trips pie fig
                        figure = company_trip_pie_fig)
                    ],
                    className='four columns',
                    style={'margin-top': '20'}
                ),
            ],
            className='row'
        ),
        # end trying to make a first row

        # redobegin trying to make a second row
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(id='trips_per_cd_fig')
                    ],
                    className='eight columns',
                    style={'margin-top': '20'}
                ),
                html.Div(
                    [
                       dcc.Graph(id='sankey_fig') # this was same name as company trips pie fig
                        #figure = company_trip_pie_fig)
                    ],
                    className='four columns',
                    style={'margin-top': '20'}
                ),
            ],
            className='row'
        ),

                                #begin trying to make a second row
        html.Div(
            [
                html.P('Filter by mobility provider:'),
                        dcc.RadioItems(
                            id='provider_selector',
                            options = company_options,
                            value=None,
                            labelStyle={'display': 'inline-block'},
                            #style={'text-align': 'center'}
                        ),
                html.P('Filter by vehicle type:'),
                        dcc.RadioItems(
                            id='mode_selector',
                            options = vehicle_options,
                            value=None,
                            labelStyle={'display': 'inline-block'},
                           # style={'text-align': 'center'}
                        ),
                html.Div(
                    [
                        dcc.Graph(id='hours_fig')
                    ],
                    #className='two columns',
                    #style={'margin-top': '20'}
                ),

            ],
            className='row'
        ),                


                                # end trying to make a row
                                
                       dcc.Graph(
                                 id = 'trips_per_cd_fig',
                                figure = trips_per_cd_fig,
                                 style = {'margin-top': '20'}
                                 ),
                        dcc.Graph(
                                id = 'sankey_fig',
                                 figure = sankey_fig,
                                style = {'margin-top': '20'}
                                ),
                       html.Div(
                                [
                                html.Div([
                                            html.Label('Select Council District'),
                                            dcc.Dropdown(id = 'cd',
                                             
                                    options = [
                                    {'label': 'Council District 1', 'value': 0},
                                    {'label': 'Council District 2', 'value': 1},
                                    {'label': 'Council District 3', 'value': 2},
                                    {'label': 'Council District 4', 'value': 3},
                                    {'label': 'Council District 5', 'value': 4},
                                    {'label': 'Council District 6', 'value': 5},
                                    {'label': 'Council District 7', 'value': 6},
                                    {'label': 'Council District 8', 'value': 7},
                                    {'label': 'Council District 9', 'value': 8},
                                    {'label': 'Council District 10', 'value': 9},
                                    {'label': 'Council District 11', 'value': 10},
                                    {'label': 'Council District 12', 'value': 11},
                                    {'label': 'Council District 13', 'value': 12},
                                    {'label': 'Council District 14', 'value': 13},
                                    {'label': 'Council District 15', 'value': 14},  
                                    ],
                                    value = 9, # default to cd 10
                                    )
                                 ]
                                 ),
                                 html.Div(
                                          [
                                           dcc.Graph(id = 'neighborhood_bar_fig',
                                                    #figure = company_trip_pie_fig,
                                                     style={'margin-top': '20'})
                                           ],
                                          ),                          
                                html.Div(
                                        [
                                           dcc.Graph(id = 'cd_hood_sankey',
                                                    #figure =  cd_hood_sankey_fig,
                                                     )
                                           ],
                                          style = {'margin-top': '20','height':'700'}
                                        ),
                                #html.Div(
                                    #    [
                                       #    dcc.Graph(id = 'trips_per_weekday_fig',
                                        #            figure =  trips_per_weekday_fig,
                                        #             )
                                        #   ],
                                        #  style = {'margin-top': '20'}
                                       # ),
                                html.Div(
                                          [
                                           dcc.Graph(id = 'avail_per_dev_fig',
                                                    figure = avail_per_dev_fig,
                                                     style = {'margin-top': '20'})
                                           ],
                                          ),
                                html.Div(
                                          [
                                           dcc.Graph(id = 'trip_starts_v_ends_fig',
                                                    figure = trip_starts_v_ends_fig,
                                                     style = {'margin-top': '20'})
                                           ],
                                          ),
                                html.Label('Select to See Locations of a Provider\'s Device Statuses'),
                                dcc.Dropdown(id= 'device status provider',
                                            options = co_opt_list,
                                           # value = [co for co in companies], fix this!
                                            value = ['Lemon'], # fix ! to work when list of vals
                                            multi = True
                                            ),
                                html.Div(
                                          [
                                           dcc.Graph(id = 'map_of_events_fig',
                                                     figure = map_fig,
                                                     style = {'margin-top': '20', 'height': '700'})
                                           ],
                                          ),
                                html.Label('Select to See Locations of a Provider\'s Device Dropoffs'),
                                dcc.Dropdown(id= 'dropoff provider',
                                            options = co_opt_list,
                                           # value = [co for co in companies], fix this!
                                            value = ['Lemon'], # fix ! to work when list of vals
                                            multi = True
                                            ),  
                                html.Div(
                                          [
                                           dcc.Graph(id = 'map_of_dropoffs_fig',
                                                     figure = dropoffs_fig,
                                                     style = {'margin-top': '20', 'height': '700'})
                                           ],
                                          ),                               
                       ]
                      
                       )
                      ]
)
                            
                                



# eturns trips that are in a specified council district
# tripdb: trips database pandas dataframe
# cd_num: council district number

def trips_starting_in_cd(tripdb,cd_num):
    boundary = all_bounds[ cd_num - 1 ] 
    co_start_points = [tripdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(tripdb))]
    co_pts = [shapely.geometry.Point(co_pt) for co_pt in co_start_points]
    bool_vec = [boundary.contains(p) for p in co_pts]   
    return tripdb.loc[bool_vec]

# Loading screen CSS
app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})

###################################################################  callbacks
# begin comment out 

# call back for sankey to from labels.
# toggle so either seeing all traffic into 1 cd or seeing all traffic out of 1 cd
# viewing either outflow or inflow. not both.
print("REComputing neighborhoods arrays for each council district...")
cd_hoods_arrays =[] # to store all of the arrays for each cd. it is an array of length 15 holding multiple dynamic arrays for each cd.
for i in range(15): # get array for hoods of all 15 cds
    cur_cd_hood_array = get_hoods_array(tdb,i)
    cd_hoods_arrays.append(cur_cd_hood_array)

# callback for when a 1 lone cd is selected, a coucil district hood bar chart is renderd
@app.callback(Output('neighborhood_bar_fig','figure'),
                [Input('cd','value')])
def update_hood_bar_fig(cdval):


    sums_starting_in_hoods = []
    sums_ending_in_hoods = []
    cdhood_array = cd_hoods_arrays[cdval]
    for i in range(len(hoods_in_cd['hood_names'][cdval])):
        sum_starting_in_hood = 0
        sum_ending_in_hood = 0
        for j in range(len(hoods_in_cd['hood_names'][cdval])):
            sum_starting_in_hood = sum_starting_in_hood + cdhood_array[i][j]
            sum_ending_in_hood = sum_ending_in_hood + cdhood_array[j][i]
        sums_starting_in_hoods.append(sum_starting_in_hood)
        sums_ending_in_hoods.append(sum_ending_in_hood)

    # get starts outside of hood bouds (sum of last row)
    sum_outofbound_starts = []
    for i in range(len(hoods_in_cd['hood_names'][cdval])+1):
        if i == len(hoods_in_cd['hood_names'][cdval]):
            outofbound_starts = 0
            for j in range(len(hoods_in_cd['hood_names'][cdval])+1):
                outofbound_starts = outofbound_starts + cdhood_array[i][j]
            sum_outofbound_starts.append(outofbound_starts)


    sum_outofbound_ends = []
    for j in range(len(hoods_in_cd['hood_names'][cdval])+1):
        if j == len(hoods_in_cd['hood_names'][cdval]):
            outofbound_starts = 0
            for i in range(len(hoods_in_cd['hood_names'][cdval])+1):
                outofbound_starts = outofbound_starts + cdhood_array[i][j]
            sum_outofbound_starts.append(outofbound_starts)

    #sumval_outofbound_start = sum(sum_outofbound_starts)
   # sumval_outofbound_end = sum(sum_outofbound_ends)

    start_trace = go.Bar(
            x=hoods_in_cd['hood_names'][cdval]+["Not in a Neighborhood"],
            y=sums_starting_in_hoods + sum_outofbound_starts,
            name="trips started"
    )
    end_trace = go.Bar(
            x=hoods_in_cd['hood_names'][cdval]+["Not in a Neighborhood"],
            y=sums_ending_in_hoods + sum_outofbound_ends,
            name="trips ended",
    )

   # data = [go.Bar(
    ##        x=hoods_in_cd['hood_names'][cdval]+["Not in a Neighborhood Bounds"],
     #       y=sums_starting_in_hoods + sum_outofbound
    #)]
    data = [start_trace,end_trace]

    lay = go.Layout(title="Trips Per Neighborhood in Council District {}".format(cdval+1) )

    
    print('row sum for this cds hoods is: ', sum(sums_starting_in_hoods))
    print('row sum for cd array for this cd is (num trip started in this cd): ', len(cd_trips[cdval]))
    return go.Figure(data=data,layout = lay)

@app.callback(Output('cd_hood_sankey','figure'),
                [Input('cd','value')])
def make_cd_hood_sankey(cdnum):
    c = []
    colors=['#%02X%02X%02X' % (r(),r(),r()) for i in range(50000)]
    cut = len(hoods_in_cd['hood_names'][cdnum])+1
    for i in range(len(hoods_in_cd['hood_bounds'][cdnum])+1):
        temp = colors[i]
        for i in range(len(hoods_in_cd['hood_bounds'][cdnum])+1):
            c.append(temp)
    def plot_cd_sankey(cd_flatlist):
        data = dict(
        type='sankey',
        width = 1118,
        height = 5118,
        node = dict(
            pad = 30,
            thickness = 20,
            line = dict(
                color = "black",
                width = 0
                ),
            label = hoods_in_cd['hood_names'][cdnum] + ["outside LA"] + hoods_in_cd['hood_names'][cdnum] + ["outside LA"],
            color = colors[:cut] + colors[:cut],
        ),
        link = dict(
            source = [i for i in range(len(hoods_in_cd['hood_bounds'][cdnum])+1) for j in range(len(hoods_in_cd['hood_bounds'][cdnum])+1)],
            target = [i+len(hoods_in_cd['hood_bounds'][cdnum])+1 for j in range(len(hoods_in_cd['hood_bounds'][cdnum])+1) for i in range(len(hoods_in_cd['hood_bounds'][cdnum])+1)], #endinds,
            value = cd_flatlist, # convert array into a flat list. array is 15 by 15 
            color = c
               )
        )

        layout =  dict(
        title = "Traffic Between Council District {} Neighborhoods".format(cdnum+1),
        font = dict(
                    size = 10
                    )
        )
        fig = dict(data=[data], layout=layout)
        return fig
    
    # define the cd flat list that you need from the specified cdnum
    cd_hoods_array = cd_hoods_arrays[cdnum]
    cd_hoods_flatlist = [item for r in cd_hoods_array for item in r]
    cd_sankey = plot_cd_sankey(cd_hoods_flatlist)
    return cd_sankey

    



# update equity sankey for the given company provider selected
@app.callback(Output('sankey_fig', 'figure'),
              [Input('provider_selector', 'value'),
              Input('mode_selector', 'value')
              ],
               )
def update_equity_sankey(provider,dev):

    tdb_new = tdb # when both are none
    if provider is not None and dev is not None:
        tdb_new = tdb_new.loc[ (tdb_new['company_name'] == COMPANIES[provider]) & (tdb_new['device_type'] == VEHICLES[dev]) ]
        dev_label = VEHICLES[dev].capitalize()
        co_label = COMPANIES[provider].capitalize()
    elif provider is None and dev is not None: # no company, but there is a device type specified
        co_label = "All"
        dev_label = VEHICLES[dev].capitalize()
        tdb_new = tdb_new.loc[  tdb_new['device_type'] == VEHICLES[dev]]
    elif dev is None and provider is not None: # no device, but there is a provider compnay specified
        tdb_new = tdb_new.loc[tdb_new['company_name'] == COMPANIES[provider]]
        co_label = COMPANIES[provider].capitalize()
        dev_label = ""
    else: # both are none
        dev_label = ""
        co_label = "All"

    new_fig = plot_equity_sankey(tdb_new)
    new_fig['layout']['title'] = "{} {} Traffic Between Equity Zones".format(co_label,dev_label)
    return new_fig 

# update trips per hour when provider is selected

@app.callback(Output('hours_fig', 'figure'),
              [Input('provider_selector', 'value'),
              Input('mode_selector','value')]
               )
def update_hours_fig(provider,dev):
    tdb_new = tdb # when both are none
    if provider is not None and dev is not None:
        tdb_new = tdb_new.loc[ (tdb_new['company_name'] == COMPANIES[provider]) & (tdb_new['device_type'] == VEHICLES[dev]) ]
        dev_label = VEHICLES[dev].capitalize()
        co_label = COMPANIES[provider].capitalize()
    elif provider is None and dev is not None: # no company, but there is a device type specified
        co_label = "All"
        dev_label = VEHICLES[dev].capitalize()
        tdb_new = tdb_new.loc[  tdb_new['device_type'] == VEHICLES[dev]]
    elif dev is None and provider is not None: # no device, but there is a provider compnay specified
        tdb_new = tdb_new.loc[tdb_new['company_name'] == COMPANIES[provider]]
        co_label = COMPANIES[provider].capitalize()
        dev_label = "Dockless"
    else: # both are none
        dev_label = "Dockless"
        co_label = "All"

    new_fig = plot_trips_per_hour(tdb_new)
    new_fig['layout']['title'] = co_label + " "+ dev_label.capitalize() + " Trips Per Hour"
    return new_fig
    




'''
@app.callback(Output('cd_start', 'value'),
              [Input('cd_end', 'value')]
               )
def toggle_start_end2(cd_end):
    if cd_end is not None:
        return None
    else:
        None
'''

@app.callback(Output('cd_start', 'value'),
              [Input('lock_selector', 'values')]
               )
def toggle_start(lock):
    if len(lock) is 0:
        None
    else:
        return None

@app.callback(Output('cd_end', 'value'),
              [Input('lock_selector', 'values')]
               )
def toggle_end(lock):
    if len(lock) is 0:
        None
    else:
        return None



# update graphs when provider_selector is chosen
# - update
'''
@app.callback(Output('company_trips_pie_fig', 'figure'),
              [Input('cd', 'value'),
              Input('mode_selector','value')],
               )
def update_trips_
'''

# update trips per company for a givenmode/vehicle type

@app.callback(Output('company_trips_pie_fig', 'figure'),
              [#Input('cd', 'value'),
              Input('mode_selector','value')]
               )
def update_trips_per_company_figure(selected_dev): # shows pie chart of trips per company
    d = tdb
    #print('selected mode value is: ',VEHICLES(selected_dev))
    #if selected_cd is 0:
     #   cd_label = "City"
    #new = plot_trips_per_company(tdb):
    #new['layout']['title'] = mode_label+' Trips Per Company in ' + cd_label
    #else:
     #   d = cd_trips[ selected_cd - 1]
     #   cd_label = "Council District " + str(selected_cd)
    if selected_dev is None:
        mode_label = "Dockless"

    elif selected_dev is not None: # if want all modes of vehicle type, do not subset
        d = d.loc[d['device_type']==VEHICLES[selected_dev]].reset_index()
        mode_label = VEHICLES[selected_dev].capitalize()
        print("number of selected devices (scooters or bikes) is: ",len(d))
    else:
        None

    newcompanies = d['company_name'].unique()
    if len(newcompanies) >= 1:
        company_trip_pie_fig = {
            "data": [
        {
        "values": [],
        "labels": [co for co in newcompanies],
        "hoverinfo": "label + value",
        "type": "pie",
        "hole":0.5
        }, 
        ],
        "layout": {
        "title": "Trips Per Company"
            }
        } 
        for co in newcompanies:
            co_users = sum(d['company_name'] == co)
            company_trip_pie_fig['data'][0]['values'].append(co_users)
        newfig = company_trip_pie_fig

    else:
        company_trip_pie_fig = {
            "data": [
        {
        "values": [0 for i in range(len(tdb['company_name'].unique() ) ) ],
        "labels": [co for co in tdb['company_name'].unique()],
        "hoverinfo": "label + value",
        "type": "pie",
        "hole":0.5
        }, 
        ],
        "layout": {
        "title": "Trips Per Company"
            }
        } 
        newfig = company_trip_pie_fig

    newfig['layout']['title'] = mode_label + ' Trips Per Company'# + cd_label
    return newfig

'''
@app.callback(Output('trips_per_weekday_fig', 'figure'),
              [Input('cd', 'value')],
               )
def update_trips_per_weekdays(selected_cd):# shows bar chart of trips per day per company in a council district
    
    if selected_cd == 0:
        d = tdb
        new_label = "City Wide"
    else:
        d = cd_trips[ selected_cd - 1]
        new_label = "in Council District " + str(selected_cd)
        #
    companies = d['company_name'].unique()

    traces=[]
    for co in companies:
        #cur_name = co
        df = d.loc[d['company_name'] ==  co].reset_index()
        
        trips_by_day = get_days_of_trips(df)

        mon_count = count_days('Monday',trips_by_day)
        tues_count = count_days('Tuesday',trips_by_day)
        wed_count  = count_days('Wednesday',trips_by_day)
        thurs_count = count_days('Thursday',trips_by_day)
        fri_count  = count_days('Friday',trips_by_day)
        sat_count  = count_days('Saturday',trips_by_day)
        sun_count = count_days('Sunday',trips_by_day)
        
        trace = go.Bar(
                       y=[mon_count,tues_count,wed_count,thurs_count,fri_count,sat_count,sun_count ],
                       x= [x for x in calendar.day_name],
                       name= co
                       )
        traces.append(trace)
    
    data=traces
    layout = go.Layout(
                       barmode='group',
                       title="Trips Per Day of Week {}".format(new_label),# from {}".format(the_interval),
                       yaxis={"title":"Number of Trips"}
                       )
        
    double_bar_fig = go.Figure(data=data, layout=layout)
    return double_bar_fig
'''

# colors for council district sankey plot nodes and linkds
colors = ['#EF431A',
    '#9F359D',
    '#34325B',
    '#84C4E0',
    '#FB606D',
    '#E1F710',
    '#7C03F1',
    '#99DC11',
    '#BAB7F7',
    '#18B994',
    '#D9804B',
    '#0C17CC',
    '#FA9D6D',
    '#557223',
    '#99FFEB',
    '#746FB1']


# arrange colors for links of sankey using colors from nodes. 2 arrangements for depicting traffic outflows vs inflows in chart.
entering_colors = [] # arranged so colors will vary by route origins when showing flows of traffic into 1 cd
for i in range(16):
    temp = colors[i]
    for i in range(16):
        entering_colors.append(temp)
        

exiting_colors = ["" for i in range(16*16)] # arranged so colors vary by route destination when showing outflow of traffic from a cd to others
for i in range(16*16):
    if i < 239:
        c = colors[i%16]
        exiting_colors[i] = c
        exiting_colors[i+16] = c
    else:
        exiting_colors[i] = colors[i%16]

@app.callback(Output('cd_sankey', 'figure'),
              [Input('cd_start', 'value'),
              Input('cd_end','value'),
              ],
               )
def update_cd_sankey(startnum,endnum): # update cd to cd sankey plot when given start and/or end points
    array_copy = deepcopy(cd_array) # 16 by 16 array with number of trips from cd to cd. rows correspond to starting cd, columns correspond to ending cd. 
    
    # make all values in 16 by 16 array 0 if they do not correspond to routes beginning in the selected origin council district
    if startnum != None and endnum is None: 
        link_colors = exiting_colors # colors vary by the destination cd of routes
        for i in range(16):
            for j in range(16):
                if i is not (startnum - 1):
                    array_copy[i][j] = 0
    # make all values in 16 by 16 array 0 if they do not correspond to routes ending in the selected destination council district
    elif endnum != None and startnum is None:
        link_colors = entering_colors #  colors vary by the origin cd of routes
        for i in range(16):
            for j in range(16):
                if j is not (endnum - 1):
                    array_copy[i][j] = 0
    # if a specific start and endpoint council district provided, return single indice value between the origin and destination cd
    elif endnum != None and startnum != None:
        link_colors = entering_colors # color based on origin when showing direct path between a cd
        for i in range(16):
            for j in range(16):
                ind = i,j
                if ind != (startnum-1,endnum-1):
                    array_copy[i][j] = 0

    # if no origin or destination cds are selected, show all trip routes between all council districts
    else:
        link_colors = entering_colors # color links based on origin 
        array_copy = array_copy
        
    # update flat list
    new_cd_flatlist = [item for r in array_copy for item in r]

    data = dict(
        type='sankey',
        width = 1118,
        height = 1118,
        node = dict(
            pad = 30,
            thickness = 20,
            line = dict(
                color = "black",
                width = 0
                ),
            label = ["CD1", "CD2","CD3","CD4", "CD5","CD6","CD7","CD8","CD9","CD10","CD11","CD12","CD13","CD14","CD15","Outside L.A.","CD1", "CD2","CD3","CD4", "CD5","CD6","CD7","CD8","CD9","CD10","CD11","CD12","CD13","CD14","CD15","Outside L.A."],
            color = colors + colors,
        ),
        link = dict(
        source = [i for i in range(16) for j in range(16)],
        target = [i+16 for j in range(16) for i in range(16)], #endinds,
        value = new_cd_flatlist, # convert array into a flat list. array is 15 by 15 
        color = link_colors
               )
        )

    layout =  dict(
        title = "Trips Between Council Districts",
        font = dict(
                    size = 10
                    )
    )
    fig = dict(data=[data], layout=layout)
    return fig 

# update dropoffs_fig when given a provider
'''
@app.callback(Output('dropoffs_fig', 'figure'),
              [Input('cd_start', 'value'),
              Input('cd_end','value'),
              ],
               )
               '''

'''
@app.callback(Output('mode_text','children'),
                    [Input('mode_selector','value')])
def change_mode_text(pickedprovider):
    return str(pickedprovider)
'''

# Main
if __name__ == '__main__':
    #with open('dashCronOutput.txt','a') as outFile:
       # outFile.write('\n dash app file is being run at ' + str(datetime.datetime.now()))
    app.server.run(debug = True, threaded = True)



