'''
This script generates an html file 'dash_testing.html' with visualizations for
the trips and status_change data.

To run in command line, provide postgres username, password, and database name argument
    
* filepaths still need to be changed for reading shapefiles
    
Author: Hannah Ross
'''

import calendar
import datetime
import plotly.plotly as py
import plotly.graph_objs as go
import sqlalchemy
import os
import json
import requests
import ast
import pandas
from mapboxgl.utils import *
from mapboxgl.viz import *
import argparse

from ast import literal_eval
import shapely
import shapely.wkt
import shapely.geometry
import sqlalchemy
import pyproj

import urllib, json
import shapefile
from shapely.geometry import shape,mapping, Point, Polygon, MultiPolygon
import shapely.ops
from osgeo import ogr
import plotly
from controls import COMPANIES, SETS
import fiona

username = SETS['username']
api_key=SETS['api_key']
plotly.tools.set_credentials_file(username=username, api_key=api_key)

def connect(user,password,db,host='localhost',port=5432):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

# retrieve data for most recent week's interval beginning as  measured by the current time script is executed and back 7 days.
def get_data(con):
    trips_db = pandas.read_sql('SELECT * FROM "trips"',con,index_col=None)
    
    #
    status_change_db = pandas.read_sql('SELECT * FROM "status_change" WHERE to_timestamp(event_time) > to_timestamp(1533416032) AND to_timestamp(event_time) < to_timestamp(1533416032)+ INTERVAL \'7 DAY\'',con, index_col=None)

#status_change_db = pandas.read_sql('SELECT * FROM "status_change"',con,
#   index_col=None)
    return (trips_db,status_change_db)

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
#parser.add_argument("filename", type=str,
#      help="path to file that contains list of urls to pull from, as well as their types")
args = parser.parse_args()

# read in trips and status_change data from the server
user = args.user
password = args.password
db = args.database
host = "localhost"
if args.host is not None:
    host = args.host
port = 5432
if args.port is not None:
    port = args.port

con = connect(user,password,db,host,port) #("hannah1ross","password","transit")
tdb, scdb = get_data(con)



# helper functions
# returns trip observations in a given month's time frame
def obs_in_month(month,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    mo = month
    bool_vec = [datetime.datetime.utcfromtimestamp(d).month==mo for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

# return trip observations in a given hour's time frame - not day specific
def obs_in_hour(hour,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    hr = hour
    bool_vec = [datetime.datetime.utcfromtimestamp(d).hour==hr for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

# return trip observations within a period of 2 specified days  (days are datetime objects)
def obs_in_days(firstday,lastday,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    bool_vec = [((datetime.datetime.utcfromtimestamp(d) >=firstday) & (datetime.datetime.utcfromtimestamp(d)<= lastday)) for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

# extracts the days of each trip for plotting trips taken per day of week
def get_days_of_trips(tripsdf):
    start_time = [tripsdf['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(tripsdf))]
    return [calendar.day_name[datetime.datetime.utcfromtimestamp(x).weekday()] for x in start_time]

# counts the frequency of each day given vector of days for plotting trips per day of week
def count_days(day,dayvec):
    vec=[dayvec[i]==day for i in range(len(dayvec))]
    return sum(vec)

# returns 3 plots for the number of trips taken per day of week (pie chart, bar plot, & double bar plot)
'''
def plot_trips_per_weekdays_for_interval(firstday,lastday,tdb ):

    trips_df = obs_in_days(firstday ,lastday , tdb)
    trips_by_day = get_days_of_trips(trips_df)
    
    mon_count = count_days('Monday',trips_by_day)
    tues_count = count_days('Tuesday',trips_by_day)
    wed_count = count_days('Wednesday',trips_by_day)
    thurs_count = count_days('Thursday',trips_by_day)
    fri_count = count_days('Friday',trips_by_day)
    sat_count= count_days('Saturday',trips_by_day)
    sun_count= count_days('Sunday',trips_by_day)
    the_interval = calendar.month_name[firstday.month] +' ' +str(firstday.day)+ ' to '+ calendar.month_name[lastday.month] +' ' +str(lastday.day)

    pie_fig = {
    "data": [
             {
             "values": [mon_count,tues_count,wed_count,thurs_count,fri_count,sat_count,sun_count ],
             "labels": [x for x in calendar.day_name],
             "type": "pie"
             },
             ],
        "layout": {
            "title":"Trips Per Day of Week from {}".format(the_interval),
        }
    }

    bar_fig = {
    "data": [
             {
             "y": [mon_count,tues_count,wed_count,thurs_count,fri_count,sat_count,sun_count ],
             "x": [x for x in calendar.day_name],
             "type": "bar"
             },
             ],
        "layout": {
            "title":"Trips Per Day of Week from {}".format(the_interval),
            "yaxis":{"title":"Number of Trips"}
            }
        }


    bat_trips_df = trips_df.loc[trips_df['company_name']=='Bat'].reset_index()
    lemon_trips_df = trips_df.loc[trips_df['company_name']=='Lemon'].reset_index()

    bat_trips_by_day = get_days_of_trips(bat_trips_df)
    lemon_trips_by_day = get_days_of_trips(lemon_trips_df)


    bat_mon_count,lemon_mon_count = count_days('Monday',bat_trips_by_day),count_days('Monday',lemon_trips_by_day),
    bat_tues_count,lemon_tues_count = count_days('Tuesday',bat_trips_by_day), count_days('Tuesday',lemon_trips_by_day)
    bat_wed_count,lemon_wed_count = count_days('Wednesday',bat_trips_by_day),count_days('Wednesday',lemon_trips_by_day)
    bat_thurs_count,lemon_thurs_count = count_days('Thursday',bat_trips_by_day),count_days('Thursday',lemon_trips_by_day)
    bat_fri_count,lemon_fri_count = count_days('Friday',bat_trips_by_day),count_days('Friday',lemon_trips_by_day)
    bat_sat_count, lemon_sat_count = count_days('Saturday',bat_trips_by_day), count_days('Saturday',lemon_trips_by_day)
    bat_sun_count, lemon_sun_count = count_days('Sunday',bat_trips_by_day),count_days('Sunday',lemon_trips_by_day)

    trace1 = go.Bar(
        y=[bat_mon_count,bat_tues_count,bat_wed_count,bat_thurs_count,bat_fri_count,bat_sat_count,bat_sun_count ],
            x= [x for x in calendar.day_name],
            name='Bat'
            )

    trace2 = go.Bar(
            y=[lemon_mon_count,lemon_tues_count,lemon_wed_count,lemon_thurs_count,lemon_fri_count,lemon_sat_count,lemon_sun_count ],
                x= [x for x in calendar.day_name],
                name='Lemon'
                )

    data=[trace1,trace2]
    layout = go.Layout(
                   barmode='group',
                   title="Trips Per Day of Week from {}".format(the_interval),
                   yaxis={"title":"Number of Trips"}
                   )

    double_bar_fig = go.Figure(data=data, layout=layout)

    return pie_fig,bar_fig,double_bar_fig

pie_fig,bar_fig,double_bar_fig = plot_trips_per_weekdays_for_interval(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 10, 8, 33, 13),tdb )
'''
def plot_trips_per_weekdays_for_interval(firstday,lastday,tdb ):
    
    init_trips_df = obs_in_days(firstday ,lastday , tdb)
    
    the_interval = calendar.month_name[firstday.month] +' ' +str(firstday.day)+ ' to '+ calendar.month_name[lastday.month] +' ' +str(lastday.day)
    
    
    
    # capture number of companies
    num_cos = len(COMPANIES)
    traces=[]
    for i in range(num_cos):
        cur_name = COMPANIES[i]
        print cur_name
        trips_df = init_trips_df
        trips_df = trips_df.loc[trips_df['company_name']==  cur_name].reset_index()
        
        
        trips_by_day = get_days_of_trips(trips_df)
        #lemon_trips_by_day = get_days_of_trips(lemon_trips_df)
        
        
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
                       name=COMPANIES[i]
                       )
                       
        traces.append(trace)
    
    data=traces
    layout = go.Layout(
                       barmode='group',
                       title="Trips Per Day of Week from {}".format(the_interval),
                       yaxis={"title":"Number of Trips"}
                       )
        
    double_bar_fig = go.Figure(data=data, layout=layout)
                       
    return double_bar_fig

double_bar_fig = plot_trips_per_weekdays_for_interval(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 10, 8, 33, 13),tdb )
# get urls of plots for trips per day
#print "Building plot: 1 of 8"
#pie_plot_url = py.plot(pie_fig, filename='trips_per_weekdayPie', auto_open=False,)
#print "Building plot: 2"
#bar_plot_url = py.plot(bar_fig, filename='trips_per_weekdayBar', auto_open=False,)
print "Building plot: 3"
double_plot_url = py.plot(double_bar_fig, filename='trips_per_weekdayDoubleBar', auto_open=False,)

# helper function used for plotting trips per hour
def to_twelve_hour(hour):
    if hour > 12:
        new=hour-12
        return str(new)+'PM'
    elif hour == 12:
        return str(hour)+ 'PM'
    elif hour == 0:
        return str(12)+ 'AM'
    else:
        return str(hour)+'AM'

# plot the number of trips taken per hour
def plot_trips_per_hour(tdb):
    start_times = [tdb['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(tdb))]
    hour_vec=[datetime.datetime.fromtimestamp(d).hour for d in start_times]
    hour_vec_ampm = [to_twelve_hour(t) for t in hour_vec]
    ampm_hours = ['12AM', '1AM','2AM','3AM','4AM','5AM', '6AM','7AM','8AM','9AM','10AM', '11AM','12PM','1PM','2PM','3PM','4PM','5PM','6PM','7PM','8PM','9PM','10PM','11PM']
    yvals=[]
    for i in range(len(ampm_hours)):
        time = ampm_hours[i]
        yvals.append(sum([(hour_vec_ampm[j]==time) for j in range(len(hour_vec_ampm))]))
    
    trace=go.Bar(x=ampm_hours,y=yvals)
    data=[trace]
    layout=go.Layout(title='Trips Taken Per Hour',barmode= 'group',bargroupgap= 0.5)
    layout.yaxis=dict(title= "Number of Trips")
    layout.xaxis={
    'type': 'date',
    'tickformat': '%H:%M',
#'tickangle':'45',
    }
    layout.xaxis=dict(title= "Hour of Day",tickmode='linear')
    layout.plot_bgcolor='rgb(11, 0, 0)'
    hours_fig=go.Figure(data=data,layout=layout)
    return py.plot(hours_fig, filename='trips_per_hour', auto_open=False,)

# can filter tdb using obs_in functions for date window specification
tdb_filtered = obs_in_days(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 10, 8, 33, 13),tdb)
print "Building plot: 4"
hours_plot_url = plot_trips_per_hour(tdb_filtered)

# creates pie chart for each companies percent of total trips taken
def plot_trips_per_company(pd_trips_df,firstday,lastday):
    dat = obs_in_days(firstday, lastday, pd_trips_df)
    the_interval = calendar.month_name[firstday.month] +' ' +str(firstday.day)+ ' to '+ calendar.month_name[lastday.month] +' ' +str(lastday.day)
    
    bat_users = sum(dat['company_name']=='Bat')
    lemon_users = sum(dat['company_name']=='Lemon')
    
    fig = {
        "data": [
                 {
                 "values": [],
                 "labels": [
                            "Bat",
                            "Lemon"
                            ],
                 "hoverinfo":"label+value",
                 "type": "pie"
                 },
                 ],
            "layout": {
            "title":"Trips Per Company from {}".format(the_interval),
                    }
                }
    fig['data'][0]['values'].append(bat_users)
    fig['data'][0]['values'].append(lemon_users)
    return py.plot(fig, filename='TripsPerCompany',auto_open=False)

print "Building plot: 5"
company_plot_url = plot_trips_per_company(tdb,datetime.datetime(2018, 8, 3, 8, 32, 13),datetime.datetime(2018, 8, 10, 8, 33, 13))

# takes in trips df, plots the number of trips taken in each council district
# for trips, does not record status change service dropoff at start of day.
# get each council district boundary'


bounds = fiona.open('/Users/hannah1ross/Desktop/mds-dev/data/CouncilDistricts.shp')# fix file path issue

all_bounds = []
for i in range(14):
    original = pyproj.Proj(bounds.crs)
    dest = pyproj.Proj(init='epsg:4326')
    polygons = []
    polygons_list = []
    for poly in bounds[i]['geometry']['coordinates']: # get district 10
        polygon = [] # eventual converted polygon
        polygon_lists = []
        for x,y in poly:
            x_prime,y_prime = pyproj.transform(original,dest,x,y) # transform point
            p = (x_prime,y_prime)
            polygon.append(p)
            polygon_lists.append([x_prime,y_prime])
    polygons.append(shapely.geometry.Polygon(polygon))
    polygons_list.append(polygon_lists)
    boundary = shapely.geometry.MultiPolygon(polygons) # o
    all_bounds.append(boundary)


def plot_trips_per_cd(tdb):
    bat_tdb = tdb.loc[tdb['company_name']=='Bat']
    lemon_tdb = tdb.loc[tdb['company_name']=='Lemon']
    lemon_tdb=lemon_tdb.reset_index()
    bat_tdb = bat_tdb.reset_index()
    bat_start_points = [bat_tdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(bat_tdb))]
    lemon_start_points = [lemon_tdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(lemon_tdb))]
    
    lemon_dc_counts = []
    bat_dc_counts = []
    # count the number of trips beginning in each of teh 15 council districts
    for i in range(len(all_bounds)):
        boundary = all_bounds[i]
        bat_dc_count = 0
        lemon_dc_count = 0
        for bat_pt,lemon_pt in zip(bat_start_points,lemon_start_points):
            bat_pt = shapely.geometry.Point(bat_pt)
            lemon_pt = shapely.geometry.Point(lemon_pt)
            if boundary.contains(bat_pt):
                bat_dc_count = bat_dc_count + 1
            if boundary.contains(lemon_pt):
                lemon_dc_count = lemon_dc_count + 1
        lemon_dc_counts.append(lemon_dc_count)
        bat_dc_counts.append(bat_dc_count)

    # plotting trips per council district (double bar per company)
    trace1 = go.Bar(
                    y=[count for count in bat_dc_counts ],
                    x= [x+1 for x in range(14)],
                    name='Bat'
                    )

    trace2 = go.Bar(
                y=[count for count in lemon_dc_counts ],
                x= [x+1 for x in range(14)],
                name='Lemon'
                )

    data=[trace1,trace2]
    layout = go.Layout(
                       barmode='group',
                       title="Trips Beginning in Each Council District",
                       yaxis={"title":"Number of Trips"},
                       xaxis={"title":"Council District"},
                       )
        
    trips_per_cd_fig = go.Figure(data=data, layout=layout)
    return py.plot(trips_per_cd_fig,auto_open = False)

print "Building plot: 6 "
trips_per_cd_url = plot_trips_per_cd(tdb)


# show chart of the most common reasons for device availability
def plot_availability_piechart(scdb):
    avail_rows = scdb.loc[scdb['event_type']=='available']
    service_start = sum(avail_rows['reason']=='service_start')
    maintenance = sum(avail_rows['reason']== 'maintenance')
    maintenance_drop_off = sum(avail_rows['reason']== 'maintenance_drop_off')
    user_drop_off = sum(avail_rows['reason']== 'user_drop_off')
    user_pick_up = sum(avail_rows['reason']== 'user_pick_up')
    low_battery = sum(avail_rows['reason']== 'low_battery')
    service_end = sum(avail_rows['reason']== 'service_end')
    rebalance_pick_up = sum(avail_rows['reason']== 'rebalance_pick_up')
    maintenance_pick_up = sum(avail_rows['reason']== 'maintenance_pick_up')
    out_of_service_area_pick_up = sum(avail_rows['reason']== 'out_of_service_area_pick_up')
    out_of_service_area_drop_off = sum(avail_rows['reason']== 'out_of_service_area_drop_off')

    fig = {
    "data": [
             {
             "values": [],
             "labels": ["service_start","maintenance","maintenance_drop_off","user_drop_off","user_pick_up","low_battery","service_end","rebalance_pick_up","maintenance_pick_up","out_of_service_area_pick_up","out_of_service_area_drop_off"],
             "name": "Availability Breakdown",
             "hoverinfo":"label+name+value",
             "type": "pie"
             },
             ],
        "layout": {
        "title":"Categories of Availability"
        }
    }

    lis = [service_start,maintenance,maintenance_drop_off,user_drop_off,user_pick_up,low_battery,service_end,rebalance_pick_up,maintenance_pick_up,out_of_service_area_pick_up,out_of_service_area_drop_off ]
    for val in lis:
        fig['data'][0]['values'].append(val)
    return py.plot(fig, filename='AvailabilityPie', auto_open=False,)

print "Building plot: 7"
availability_pie_url = plot_availability_piechart(scdb)


# create a sankey plot for each company for flows of trips between equity zones
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


city_boundary = read_area('/Users/hannah1ross/Desktop/mds-dev/data/City_Boundary.shp')
sf_equity = read_area('/Users/hannah1ross/Desktop/mds-dev/data/San_Fernando_Valley.shp')
non_sf_equity = read_area('/Users/hannah1ross/Desktop/mds-dev/data/Non_San_Fernando.shp')

lemon_trips = tdb.loc[tdb['company_name']=='Lemon'].reset_index()
bat_trips = tdb.loc[tdb['company_name']=='Bat'].reset_index()

lemon_trip_starts = [] # list of lat longs to be converted into geometry points Points
bat_trip_starts = []
for i in range(len(lemon_trips)):
    lemon_trip_starts.append(lemon_trips['route'][i]['features'][0]['geometry']['coordinates'])
for i in range(len(bat_trips)):
    bat_trip_starts.append(bat_trips['route'][i]['features'][0]['geometry']['coordinates'])

lemon_trip_ends = []
bat_trip_ends = []
for i in range(len(lemon_trips)):
    lemon_trip_ends.append(lemon_trips['route'][i]['features'][1]['geometry']['coordinates'])
for i in range(len(bat_trips)):
    bat_trip_ends.append(bat_trips['route'][i]['features'][1]['geometry']['coordinates'])


# currently only council district 10 so there will be NO TRIPS STARTS OR ENDS IN THE SF VALLEY EQUITY ZONE
val_to_val = 0
val_to_nonval = 0
val_to_city = 0

nonval_to_nonval = 0
nonval_to_val = 0
nonval_to_city = 0

city_to_city = 0
city_to_val = 0
city_to_nonval = 0

for i in range(len(lemon_trip_starts[-1000:-1])):
    startpt = shapely.geometry.Point(lemon_trip_starts[i])
    endpt = shapely.geometry.Point(lemon_trip_ends[i])
    if (sf_equity.contains(startpt)):
        if non_sf_equity.contains(endpt):
            val_to_nonval=val_to_nonval + 1
        elif sf_equity.contains(endpt):
            val_to_val = val_to_val + 1
        else:
            val_to_city = val_to_city + 1
    elif (non_sf_equity.contains(startpt)):
        # print "made it here", i
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

# hard code to compensate for only district 10 points
val_to_val = 100
val_to_nonval = 20
val_to_city = 32

nonval_to_val = 20
city_to_val = 120

data = dict(
            type='sankey',
            node = dict(
                        pad = 10,
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
    
layout =  dict(
                   title = "Lemon Trip Paths by Equity Zone <br>",
                   font = dict(
                               size = 12
                               ),
                   updatemenus= [
                                 dict(
                                      y=1,
                                      buttons=[
                                               dict(
                                                    label='Light',
                                                    method='relayout',
                                                    args=['paper_bgcolor', 'white']
                                                    ),
                                               dict(
                                                    label='Dark',
                                                    method='relayout',
                                                    args=['paper_bgcolor', 'grey']
                                                    )
                                               ]
                                      
                                      ),
                                 dict(
                                      y=0.6,
                                      buttons=[
                                               dict(
                                                    label='Horizontal',
                                                    method='restyle',
                                                    args=['orientation', 'h']
                                                    ),
                                               dict(
                                                    label='Vertical',
                                                    method='restyle',
                                                    args=['orientation', 'v']
                                                    )
                                               ]
                                      
                                      )
                                 ]
                   )


fig = dict(data=[data], layout=layout)
print "Building plot: 8 "
lemon_sankey_plot_url = py.plot(fig, validate=False,auto_open=False)


# create map of event_types
scdb_small = scdb.head(100)
start_points =[literal_eval(scdb_small['location'][i]) for i in scdb_small['location'].index]
events = [scdb_small['event_type'][i] for i in range(len(scdb_small))]

# create dataframes for startpoints and endpoints with lat and long coords
start_d = {'lat':[], 'lon':[],'event_type':[]}

for start_p in start_points:
    start_lon,start_lat = start_p[0],start_p[1]
    start_d['lat'].append(start_lat)
    start_d['lon'].append(start_lon)

for event_type in events:
    start_d['event_type'].append(event_type)

startdb = pandas.DataFrame.from_dict(start_d)
WELL_COLORS = dict(available= 'rgb(139,195,74)', unavailable = 'yellow', reserved= 'rgb(2,136,209)', removed='rgb(211,47,47)' )
traces = []
for ev_type, dff in startdb.groupby('event_type'):
    trace = dict(
                 type='scattermapbox',
                 lon=dff['lon'],
                 lat=dff['lat'],
                 name= ev_type,
                 text = ev_type,
                 marker=dict(
                             size=11,
                             opacity=1,
                             color=WELL_COLORS[ev_type]
                             ),
                 )
    traces.append(trace)

lay = go.Layout()
lay['hovermode']='closest'
lay['autosize'] = True
lay['mapbox']['zoom'] = 11
lay['mapbox']['center']=dict(
                             lon=-118.33,
                             lat=34.017)
lay['mapbox']['bearing']=0
lay['title'] = 'Location of Scooter Statuses<br>(select legend to inspect an event type)'

map_fig = go.Figure(data = traces,layout = lay)
print "Building plot: 9"
event_map_url = py.plot(map_fig,auto_open=False)

# configure the html with all plot urls
html_string = '''
    <html>
    <link rel="stylesheet" href="https://unpkg.com/react-select@1.0.0-rc.3/dist/react-select.min.css">
    <link rel="stylesheet" href="https://unpkg.com/react-virtualized@9.9.0/styles.css">
    
    <link rel="stylesheet" href="https://unpkg.com/react-virtualized-select@3.1.0/styles.css">
    <link rel="stylesheet" href="https://unpkg.com/rc-slider@6.1.2/assets/index.css">
    
    <div class="row"><h1 class="eight columns">LADOT Dockless Dashboard - Weekly Overview</h1><img class="one columns" src="https://static1.squarespace.com/static/5952a8abbf629aef69513d41/t/595565dd4f14bc185894d47d/1498768870821/New+LADOT+Logo.png" style="height: 100px; position: relative; float: right; width: 225px;"></div>

    <!-- *** Section 1 *** --->
    
    
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + double_plot_url + '''.embed?width=800&height=550"></iframe>
        
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + hours_plot_url + '''.embed?width=900&height=550"></iframe>
            
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + company_plot_url + '''.embed?width=900&height=550"></iframe>
            
            
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
            src="''' + trips_per_cd_url + '''.embed?width=900&height=550"></iframe>
            
      
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="yes" \
                src="''' + availability_pie_url + '''.embed?width=900&height=550"></iframe>
        
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + lemon_sankey_plot_url + '''.embed?width=900&height=550"></iframe>
                    
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="yes" \
                    src="''' + event_map_url + '''.embed?width=900&height=550"></iframe>
                    
            </html>
 '''
print('Generating \'dash_testing.html\' ...')
f = open('dash_testing.html','w')
f.write(html_string)
f.close()
print('Done.')






