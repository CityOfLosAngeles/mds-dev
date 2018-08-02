"""
    Running this script in command line generates a link to a Dash application with visualizations on local server.
    - currently, username and file paths need to be changed for connect, read_bounds, and read_area
    - mapping capabilities not yet functional
    
    Author: Hannah Ross
    """

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
import fiona # KEEP FIONA AFTER SHAPELY IMPORTS

app = dash.Dash(__name__)
app.css.append_css({'external_url': 'https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css'})  # noqa: E501
server = app.server
CORS(server)

if 'DYNO' in os.environ:
    app.scripts.append_script({
                              'external_url': 'https://cdn.rawgit.com/chriddyp/ca0d8f02a1659981a0ea7f013a378bbd/raw/e79f3f789517deec58f41251f7dbb6bee72c44ab/plotly_ga.js'  # noqa: E501
                              })


# read in data from server
def connect(user,password,db,host='localhost',port=5432):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

def get_data(con):
    trips_db = pandas.read_sql('SELECT * FROM "trips"',con,index_col=None)
    status_change_db = pandas.read_sql('SELECT * FROM "status_change"',con,
                                       index_col=None)
    return (trips_db,status_change_db)

# read in trips and status change data from the server
print ("Loading in data...")
con = connect("hannah1ross","password","transit")
tdb, scdb = get_data(con)

'''
    ########################################################## create map of event_types
    
    print ("Generating event status map...")
    
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
    #accesstoken=mapbox_access_token,
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
    lon=startd['lon'],
    lat=startd['lat'],
    # name= ev_type,
    text = startd['event_type'],
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
    '''

# make bar chart for trips per cd
print("Generating plot of trips per council district...")

def read_bounds(filename):
    bounds = fiona.open('/Users/hannah1ross/Desktop/mds-dev/data/'+filename)# fix file path issue
    return bounds
bounds= read_bounds('CouncilDistricts.shp')

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

def plot_trips_per_cd(tdb_new):
    bat_tdb = tdb_new.loc[tdb_new['company_name']=='Bat']
    lemon_tdb = tdb_new.loc[tdb_new['company_name']=='Lemon']
    lemon_tdb=lemon_tdb.reset_index()
    bat_tdb = bat_tdb.reset_index()
    bat_start_points = [bat_tdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(bat_tdb))]
    lemon_start_points = [lemon_tdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(lemon_tdb))]
    
    lemon_dc_counts = []
    bat_dc_counts = []
    
    # count the number of trips beginning in each of the 15 council districts
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
    return trips_per_cd_fig

trips_per_cd_fig = plot_trips_per_cd(tdb.head(120))

'''
    # generate pie chart of trips per company
    print("Generating pie chart of trips per company...")
    tdb_small = tdb.head(1000)
    bat_users = sum(tdb_small['company_name']=='Bat')
    lemon_users = sum(tdb_small['company_name']=='Lemon')
    
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
    "title":"Trips Per Company from {}"#.format(the_interval),
    }
    }
    company_trip_pie_fig['data'][0]['values'].append(bat_users)
    company_trip_pie_fig['data'][0]['values'].append(lemon_users)
    
    # make sankey plot for flows between equity zones
    # currently only council district 10 so there will be no trip starts or ends in the sf valley equity zone
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
    
    
    city_boundary = read_area('/Users/hannah1ross/Desktop/mds-dev/data/City_Boundary.shp')
    sf_equity = read_area('/Users/hannah1ross/Desktop/mds-dev/data/San_Fernando_Valley.shp')
    non_sf_equity = read_area('/Users/hannah1ross/Desktop/mds-dev/data/Non_San_Fernando.shp')
    
    
    lemon_trips = tdb.loc[tdb['company_name']=='Lemon'].reset_index()
    bat_trips = tdb.loc[tdb['company_name']=='Bat'].reset_index()
    
    lemon_trip_starts = []
    bat_trip_starts = []
    lemon_trip_ends = []
    bat_trip_ends = []
    for i in range(len(lemon_trips)):
    lemon_trip_starts.append(lemon_trips['route'][i]['features'][0]['geometry']['coordinates'])
    lemon_trip_ends.append(lemon_trips['route'][i]['features'][1]['geometry']['coordinates'])
    for i in range(len(bat_trips)):
    bat_trip_starts.append(bat_trips['route'][i]['features'][0]['geometry']['coordinates'])
    bat_trip_ends.append(bat_trips['route'][i]['features'][1]['geometry']['coordinates'])
    val_to_val = 0
    val_to_nonval = 0
    val_to_city = 0
    
    nonval_to_nonval = 0
    nonval_to_val = 0
    nonval_to_city = 0
    
    city_to_city = 0
    city_to_val = 0
    city_to_nonval = 0
    
    for i in range(len(lemon_trip_starts)):
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
    
    # hard coded to compensate for only district 10 points/ absence of valley points
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
    
    sankey_fig = go.Figure(data=[data], layout=layout)
    '''
# Create app layout
app.layout = html.Div(
                      [
                       html.Div(
                                [
                                 html.H1(
                                         'LADOT Dockless eScooter Dashboard - Weekly Overview',
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
                                 id='event_fig',
                                 #figure = trips_per_cd_fig,
                                 #figure= event_fig,
                                 style={'margin-top': '20'}
                                 ),
                       html.Div(
                                [
                                 html.Div(
                                          [
                                           dcc.Graph(id='trips_per_cd_fig',
                                                     figure = trips_per_cd_fig)
                                           ],
                                          className='four columns',
                                          style={'margin-top': '10'}
                                          ),
                                 html.Div(
                                          [
                                           dcc.Graph(id='sankey_fig',
                                                     #figure = sankey_fig,
                                                     style={'margin-top': '20'})
                                           ],
                                          #className='four columns',
                                          #style={'margin-top': '20'}
                                          ),
                                 html.Div(
                                          [
                                           dcc.Graph(id='company_trips',
                                                     #figure = company_trip_pie_fig
                                                     )
                                           ],
                                          className='four columns',
                                          style={'margin-top': '10'}
                                          ),
                                 ],
                                className='row'
                                ),
                       ]
                      )

'''
    app.layout = html.Div([
    dcc.Graph(id='graph'),
    dcc.Input(id='input',value  =  'Bat',type ='text')
    ])
    
    @app.callback(Output(component_id='graph', component_property='figure'),
    [Input('input', 'value')])
    def update_output_graph(myinput):
    layout =  dict(
    title = myinput + " Trip Paths by Equity Zone <br>",
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
    
    trips = tdb.loc[tdb['company_name']== myinput].reset_index()
    
    trip_starts = []
    
    trip_ends = []
    
    for i in range(len(trips)):
    trip_starts.append(trips['route'][i]['features'][0]['geometry']['coordinates'])
    trip_ends.append(trips['route'][i]['features'][1]['geometry']['coordinates'])
    
    
    val_to_val = 0
    val_to_nonval =0
    val_to_city = 0
    
    nonval_to_nonval = 0
    nonval_to_val = 0
    nonval_to_city = 0
    
    city_to_city = 0
    city_to_val = 0
    city_to_nonval = 0
    
    for i in range(len(trip_starts[-1000:-1])):
    startpt = shapely.geometry.Point(trip_starts[i])
    endpt = shapely.geometry.Point(trip_ends[i])
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
    sankey_fig = go.Figure(data=[data], layout=layout)
    
    
    return sankey_fig
    '''



# In[]:
# Main
if __name__ == '__main__':
    app.server.run(debug=False)


