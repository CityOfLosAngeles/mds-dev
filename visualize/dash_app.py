"""
    Running this script generates a locally hosted Dash application with figures contructed from the transit SQL database.
    - currently, username and file paths need to be changed for connect, read_bounds, and read_area
    - mapping capabilities not yet functional
    - this script requires neccessary views: availability,
    - currently end points are computer as the second point in route.
    
    to use:    python dash_app.py [username] [password] [database name]

    Author: Hannah Ross
"""
import argparse
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
import fiona # MUST KEEP FIONA IMPORT AFTER SHAPELY IMPORTS
import controls # controls allows for modularity with company names, plotly account settings, 
app = dash.Dash(__name__)
app.css.append_css({'external_url': 'https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css'})  # noqa: E501
server = app.server
CORS(server)

if 'DYNO' in os.environ:
    app.scripts.append_script({
                              'external_url': 'https://cdn.rawgit.com/chriddyp/ca0d8f02a1659981a0ea7f013a378bbd/raw/e79f3f789517deec58f41251f7dbb6bee72c44ab/plotly_ga.js'  # noqa: E501
                              })


################################################## read in data from server
def connect(user,password,db,host='localhost',port=5432):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

def get_data(con):
    trips_db = pandas.read_sql('SELECT * FROM "trips"',con,index_col=None)
    status_change_db = pandas.read_sql('SELECT * FROM "status_change"',con,
                                       index_col=None) # fix: adjust command to read in most recent week
    return (trips_db,status_change_db)


print ("Loading in server data...")
# extract arguments to connect to server
parser = argparse.ArgumentParser()
parser.add_argument("user", type=str,
                    help="username to access postgresql database")
parser.add_argument("password", type=str,
                    help="password to access postgresql database")
parser.add_argument("database", type=str,
                    help="database name")
args = parser.parse_args()

user = args.user
password = args.password
db = args.database

con = connect(user,password,db)
tdb, scdb = get_data(con)

################################################ extract company names and the number of companies
companies = tdb['company_name'].unique()

################################################# read in council district boundaries
print("Loading in council district shapefiles...")

# function to read in council district boundaries
def read_bounds(filename):
    bounds = fiona.open('/Users/newmobility/Desktop/mds-dev/data/shapefiles/'+filename)# fix file path issue
    return bounds

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

# fix how the order of bounds in shapefiles is random with respect to council districts
myorder=[10, 4, 3, 6, 5, 2, 0, 13, 12, 11, 9, 1, 7, 8, 14]
all_bounds = [ all_bounds[i] for i in myorder]


################################################  preproccess trips for each council district
def trips_in_cd(tripdb,cd_num):
    boundary = all_bounds[ cd_num-1 ] 
    co_start_points = [tripdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(tripdb))]
    co_pts = [shapely.geometry.Point(co_pt) for co_pt in co_start_points]
    bool_vec = [boundary.contains(p) for p in co_pts]   
    return tripdb.loc[bool_vec]

# extract each cd's trips for querying
cd_trips = []
for i in range(1,16,1):
    cd_trips.append(trips_in_cd(tdb,i))



########################################################## create map of event_types
'''


print ("Generating event status map...")
#OLD

layout = dict(
    autosize=True,
    height=500,
    font=dict(color='#CCCCCC'),
    titlefont=dict(color='#CCCCCC', size='14'),
    margin=dict(
    l=35,
    r=35,
    b=35,
    t=45
    ),
    hovermode="closest",
    plot_bgcolor="#191A1A",
    paper_bgcolor="#020202",
    legend=dict(font=dict(size=10), orientation='h'),
    title='Satellite Overview',
    mapbox=dict(
    accesstoken='pk.eyJ1IjoiaGFubmFocm9zczMzIiwiYSI6ImNqajR3aHcwYzFuNWcza3BnNzVoZzQzcHQifQ.eV_IJn3AdBE3n57rd2fhFA',
    style="dark",
    center=dict(
    lon=-78.05,
    lat=42.54
    ),
    zoom=7,
    )
    )
    
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
 #for ev_type, dff in startdb.groupby('event_type'):
trace = dict(
    type='scattermapbox',
    lon=startdb['lon'],
    lat=startdb['lat'],
    # name= ev_type,
    text = startdb['event_type'],
    marker=dict(
    size=11,
    opacity=1,
    #color=WELL_COLORS[ev_type]
    ),
    )
traces.append(trace)
    
    
lay = go.Layout()
    #lay['hovermode']='closest'
    #lay['autosize'] = True
    #lay['mapbox']['zoom'] = 11
lay['mapbox']['center']=dict(
    lon=-118.33,
    lat=34.017)
    #lay['mapbox']['bearing']=0
event_fig = go.Figure(data = traces,layout = lay)


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
lay['title'] = 'Locations of Scooter Statuses'

map_fig = go.Figure(data = traces,layout = lay)


'''
############################################### create bar chart for trips per council district
print("Generating plot of trips per council district...")

# creates double-bar chart for the number of trips taken in each council district per company
def plot_trips_per_cd(tdb):
    traces = []
    for co in companies:
        co_dc_counts = []
        for df in cd_trips:
            co_df = df.loc[df['company_name']== co]
            co_df = co_df.reset_index()
        #co_start_points = [co_tdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(co_tdb))]
        #co_dc_counts = [] # count co devices in each of the council districts
        # count the number of trips beginning in each of the council districts
        #for i in range(len(all_bounds)):
        #    boundary = all_bounds[i]
        #    co_dc_count = 0
        #    for co_pt in co_start_points:
        #        co_pt = shapely.geometry.Point(co_pt)
         #       if boundary.contains(co_pt):
         #           co_dc_count = co_dc_count + 1
            co_dc_count = len(co_df)#.append(co_dc_count)
            co_dc_counts.append(co_dc_count)
        trace = go.Bar(
                    y = co_dc_counts,
                    x = [x for x in range(1,16,1)],
                    name=str(co)
                    )
        traces.append(trace)
    data= traces
    layout = go.Layout(
                       barmode='group',
                       title="Trips Beginning in Each Council District",
                       yaxis={"title":"Number of Trips"},
                       xaxis={"title":"Council District"},
                       )            
    trips_per_cd_fig = go.Figure(data=data, layout=layout)
    return trips_per_cd_fig

trips_per_cd_fig = plot_trips_per_cd(tdb)

def plot_cd_start_and_ends(tdb):
    for i in range(len(tdb)):
        cur_len = len(tdb['route'][i]['features'])
        co_end_points = tdb['route'][i]['features'][cur_len - 1]['geometry']['coordinates'] 
        co_start_points = tdb['route'][i]['features'][cur_len - 1]['geometry']['coordinates'] 
    
    




################################################ create pie chart of trips per company
print("Generating pie chart of trips per company...")
def plot_trips_per_company(tdb):
    company_trip_pie_fig = {
            "data": [
        {
        "values": [],
        "labels": [co for co in companies],
        "hoverinfo":"label+value",
        "type": "pie"
        },
        ],
        "layout": {
        "title":"Trips Per Company"# from {}".format(the_interval),
         }
    } 
    for co in companies:
        co_users = sum(tdb['company_name']==co)
        company_trip_pie_fig['data'][0]['values'].append(co_users)

    return company_trip_pie_fig

company_trip_pie_fig = plot_trips_per_company(tdb)
    
############################################# create sankey figure for equity zone flows
# *currently only council district 12 so there will be no trip starts or ends in the sf valley equity zone
print("Generating equity zone sankey plot...")

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
    
# read in equity zone boundaries
city_boundary = read_area('/Users/newmobility/Desktop/mds-dev/data/shapefiles/City_Boundary.shp')
sf_equity = read_area('/Users/newmobility/Desktop/mds-dev/data/shapefiles/San_Fernando_Valley.shp')
non_sf_equity = read_area('/Users/newmobility/Desktop/mds-dev/data/shapefiles/Non_San_Fernando.shp')


# def plot_equity_sankey   ** make it so you can feed it a trips database for each company
def plot_equity_sankey(tdb):
    co_trip_starts = []
    co_trip_ends = []
    for i in range(len(tdb)):
        co_trip_starts.append(tdb['route'][i]['features'][0]['geometry']['coordinates'])
        co_trip_ends.append(tdb['route'][i]['features'][1]['geometry']['coordinates'])

    # if length is > 1 do not label title with company
    val_to_val = 0
    val_to_nonval = 0
    val_to_city = 0
    nonval_to_nonval = 0
    nonval_to_val = 0
    nonval_to_city = 0
    city_to_city = 0
    city_to_val = 0
    city_to_nonval = 0

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

    # hard coded numbers to compensate for only district 10 points in fake data
    val_to_val = 100000
    val_to_nonval = 20000
    val_to_city = 32000
    nonval_to_val = 20000
    city_to_val = 120000

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
    if len(tdb['company_name'].unique()) is 1:
        co = tdb['company_name'].unique()[0]
    else:
        co = "Total"

    layout =  dict(
                   title = "{} Trip Paths by Equity Zone <br>".format(co),
                   font = dict( 
                               size = 12
                               ),
                   updatemenus= [
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

    sankey_fig = go.Figure(data=[data], layout=layout)
    return sankey_fig

sankey_fig = plot_equity_sankey(tdb) # will plot total equity flows 

# plot sankey for each company
#for co in companies:
 #   d = tdb.loc[tdb['company_name']==co]
 #   plot = plot_equity_sankey(d)



############################################# create bar chart for trips per hour
# helper function for trips per hour
def obs_in_days(firstday,lastday,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    bool_vec = [((datetime.datetime.utcfromtimestamp(d) >=firstday) & (datetime.datetime.utcfromtimestamp(d)<= lastday)) for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

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

# plots the number of trips taken per hour as a bar chart
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
    }
    layout.xaxis=dict(title= "Hour of Day",tickmode='linear')
    layout.plot_bgcolor='rgb(11, 0, 0)'
    hours_fig=go.Figure(data=data,layout=layout)
    return hours_fig

# can filter trips database using obs_in functions for date window specification
tdb_filtered = obs_in_days(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 10, 8, 33, 13),tdb)
print("Generating trips per hour figure...")
hours_plot_fig = plot_trips_per_hour(tdb_filtered)

########################################################## create plot of 24 hour availabilities per device ratios
import numpy
# to read in availability view from server
def get_availability(con):
    availability_db = pandas.read_sql('SELECT * FROM "availability"',con,index_col=None)
    return availability_db

# read in availability view from the server
print("Reading in availability view")
availdb = get_availability(con)

# helper function for availability ratio plot that returns the number of availability periods in a given hour from availability view
def avail_dev_in_hour(hour,pd_df): 
    start_time = [time for time in pd_df['start_time']]
    end_time = [time for time in pd_df['end_time']]
    hr = hour
    count = 0
    for i in range(len(end_time)): 
        t_s = start_time[i]
        t_e = end_time[i]
       # print("t_e  is: ",t_e )
        if numpy.isnan(t_e):
            break
        if numpy.isnan(t_s):
            break
        if datetime.datetime.utcfromtimestamp(t_s).hour==hr:
            count = count + 1
        elif datetime.datetime.utcfromtimestamp(t_s).hour<hr and datetime.datetime.utcfromtimestamp(t_e).hour>hr:
            count = count + 1
        elif datetime.datetime.utcfromtimestamp(t_e).hour==hr:
            count = count + 1
        else:
            None
    return count

print("Generating availability ratio plot...")

# get both companies' availability view rows
lemon_avail = availdb.loc[availdb['company_name']=='Lemon']
bat_avail = availdb.loc[availdb['company_name']=='Bat']

# compute the unique devices for count of deployed devices per company
num_bat = len(bat_avail['device_id'].unique())
num_lemon = len(lemon_avail['device_id'].unique())

tot_bat_dev_per_24hour = [num_bat]* 24
tot_lemon_dev_per_24hour = [num_lemon]* 24

# compute the number of available windows during each of 24 hours ** counting overlapping hours too
tot_bat_avail_per_24hour=[]
tot_lemon_avail_per_24hour=[]

for i in range(0,24,1):
    batavail = avail_dev_in_hour(i,bat_avail)
    lemonavail = avail_dev_in_hour(i,lemon_avail)
    tot_bat_avail_per_24hour.append(batavail)
    tot_lemon_avail_per_24hour.append(lemonavail)

# adjust zeros for ratio calculation 
bat_zeros=[]
lemon_zeros=[]
for i in range(len(tot_bat_avail_per_24hour)):#,tot_lemon_avail_per_24hour):
    if tot_bat_avail_per_24hour[i] == 0: # record indices with zeros to allow for dividing by 0 for ratio calculations
        bat_zeros.append(i)
    if tot_lemon_avail_per_24hour[i] == 0:
        lemon_zeros.append(i)
               
for i in bat_zeros:
    tot_bat_avail_per_24hour[i] = 0.01
for i in lemon_zeros:
    tot_lemon_avail_per_24hour[i]=0.01

# compute number of availability windows per device: # availibility / total devices
lemon_avail_ratio = [float(tot_lemon_avail_per_24hour[i]) / tot_lemon_dev_per_24hour[i] for i in range(24)]#num avail  per num devices
bat_avail_ratio = [float(tot_bat_avail_per_24hour[i]) / tot_bat_dev_per_24hour[i] for i in range(24)]# num avail  per num devices

# Create a trace
import plotly.graph_objs as go
import plotly.plotly as py

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
    x = [x for x in range(0,24,1)],
    y = [2]* 24, # fix this to be the standard ratio of avail per device
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
              yaxis = dict(title = 'Availabilities per Device'),
              )
avail_per_dev_fig = go.Figure(data = data, layout = layout)

#################################################################### Create app layout
app.layout = html.Div(
                      [
                       html.Div(
                                [
                                 html.H1(
                                         'Dockless Scooter Dashboard - Weekly Overview',
                                         className='eight columns',
                                         ),
                                 html.Img(
                                          src="https://static1.squarespace.com/static/5952a8abbf629aef69513d41/t/595565dd4f14bc185894d47d/1498768870821/New+LADOT+Logo.png",
                                          className='one columns',
                                          style={
                                          'height': '100',
                                          'width': '225',
                                          'float': 'right',
                                          'position': 'relative',
                                          },
                                          ),
                                 ],
                                className='row'
                                ),
                       dcc.Graph(
                                 id='trips_per_cd_fig',
                                 figure = trips_per_cd_fig,
                                 style={'margin-top': '20'}
                                 ),
                        dcc.Graph(
                                id='sankey_fig',
                                 figure = sankey_fig,
                                style={'margin-top': '20'}
                                ),
                       html.Div(
                                [
                                html.Div([
                                            html.Label('Select Council District'),
                                            dcc.Dropdown(id = 'cd',
                                             
                                    options=[
                                    {'label': 'Total City Aggregate', 'value': None},
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
                                    ],
                                    value=None,
                                    )
                                 ]
                                 ),
                                 html.Div(
                                          [
                                           dcc.Graph(id='company_trips_fig',
                                                     figure = company_trip_pie_fig,
                                                     style={'margin-top': '20'})
                                           ],
                                          ),
                                 html.Div(
                                          [
                                           dcc.Graph(id='hours_fig',
                                                     figure =  hours_plot_fig,
                                                     )
                                           ],
                                          style={'margin-top': '20'}
                                          ),
                                html.Div(
                                          [
                                           dcc.Graph(id='avail_per_dev_fig',
                                                    figure = avail_per_dev_fig,
                                                     style={'margin-top': '20'})
                                           ],
                                          ),
                                html.Div(
                                          [
                                           dcc.Graph(id='map_of_events_fig',
                                                     #figure = map_fig,
                                                     style={'margin-top': '20'})
                                           ],
                                          ),                                
                       ]
                      
                       )
                      ]
)



# helper function returns trips that are in a specified council district
def trips_in_cd(tripdb,cd_num):
    print(type(cd_num))
    boundary = all_bounds[ cd_num-1 ] 
    co_start_points = [tripdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(tripdb))]
    co_pts = [shapely.geometry.Point(co_pt) for co_pt in co_start_points]
    bool_vec = [boundary.contains(p) for p in co_pts]   
    return tripdb.loc[bool_vec]

@app.callback(Output('company_trips_fig', 'figure'),
              [Input('cd', 'value')],
               )
def update_company_figure(selected_cd):
    #if cd=='1':
     #   d = trips_in_cd(tdb,1)
    #else:
    #    d=tdb
    print(selected_cd)
    if selected_cd is None:
        d = tdb
        new_label = "City Wide"
    else:
        d= cd_trips[selected_cd -1]
        new_label = "in Council District " + str(selected_cd)
    bat_users = sum(d['company_name']=='Bat')
    lemon_users = sum(d['company_name']=='Lemon')
    
    company_trip_pie_fig = {
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
    "title":"Trips Per Company {}".format(new_label),
    }
    }
    company_trip_pie_fig['data'][0]['values'].append(bat_users)
    company_trip_pie_fig['data'][0]['values'].append(lemon_users)
    return company_trip_pie_fig

@app.callback(Output('hours_fig', 'figure'),
              [Input('cd', 'value')],
               )
def update_hour_fig(selected_cd):
    t = cd_trips[selected_cd -1]
    start_times = [t['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(t))]
    hour_vec=[datetime.datetime.fromtimestamp(d).hour for d in start_times]
    hour_vec_ampm = [to_twelve_hour(t) for t in hour_vec]
    ampm_hours = ['12AM', '1AM','2AM','3AM','4AM','5AM', '6AM','7AM','8AM','9AM','10AM', '11AM','12PM','1PM','2PM','3PM','4PM','5PM','6PM','7PM','8PM','9PM','10PM','11PM']
    yvals=[]
    for i in range(len(ampm_hours)):
        time = ampm_hours[i]
        yvals.append(sum([(hour_vec_ampm[j]==time) for j in range(len(hour_vec_ampm))]))
    
    trace=go.Bar(x=ampm_hours,y=yvals)
    data=[trace]
    if selected_cd is not None:
        layout = layout=go.Layout(title='Trips Taken Per Hour in Council District {}'.format(str(selected_cd)),barmode= 'group',bargroupgap= 0.5)
    else:
        layout=go.Layout(title='Total Trips Taken Per Hour',barmode= 'group',bargroupgap= 0.5)
    layout.yaxis=dict(title= "Number of Trips")
    layout.xaxis={
    'type': 'date',
    'tickformat': '%H:%M',
    }
    layout.xaxis=dict(title= "Hour of Day",tickmode='linear')
    layout.plot_bgcolor='rgb(11, 0, 0)'
    hours_fig=go.Figure(data=data,layout=layout)
    return hours_fig

# In[]:
# Main
if __name__ == '__main__':
    app.server.run(debug=False,threaded=True)




'''
# bar chart plot for trip starts and ends per council district
import plotly.graph_objs as go
import plotly.plotly as py
def plot_cd_start_and_ends(tdb):
    co_end_points = []
    co_start_points = []
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
    
    trace = go.Bar(
                    y = total_cd_starts,
                    x = [x for x in range(1,16,1)],
                    name="trip starts",
                marker=dict(
                color='green'
                    )
    )
    trace2 = go.Bar(y= total_cd_ends, x = [x for x in range(1,16,1)],name="trip ends",marker=dict(
        color='red'))
    data= [trace,trace2]
    layout = go.Layout(
                       barmode='group',
                       title="Trip Starts and Ends Per Council District",
                       yaxis={"title":"Counts"},
                       xaxis={"title":"Council District"},
                       )            
    trips_per_cd_fig = go.Figure(data=data, layout=layout)
    return trips_per_cd_fig
'''