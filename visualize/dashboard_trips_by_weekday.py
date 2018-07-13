'''
    This notebook will generate an html file to serve as a precursor for a dashboard file.
    Current visuals: trips per day of week (pie chart, bar plot, grouped bar plot, time of trips plot)
    ** modified for new dabase structure
    
    Name and Password fields will need to be changed for 'connect'.
    
    Author: Hannah Ross
'''

import calendar
import datetime
import plotly.plotly as py
import sqlalchemy
from mapbox import Datasets
import os
from mapboxgl.utils import create_color_stops
from mapboxgl.viz import CircleViz
import psycopg2
import pandas
import json
import requests
import ast
import pandas as pd
from mapboxgl.utils import *
from mapboxgl.viz import *
import plotly.graph_objs as go

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
con = connect("hannah1ross","password","transit")
tdb, scdb = get_data(con)

# returns observations in a given month's time frame
def obs_in_month(month,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    mo = month
    vec=[datetime.datetime.utcfromtimestamp(x) for x in start_time[0:len(pd_df)] if datetime.datetime.utcfromtimestamp(x).month==mo]
    bool_vec = [d.month==mo for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

# return observations in a given hour's time frame - not day specific
def obs_in_hour(hour,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    hr = hour
    vec=[datetime.datetime.utcfromtimestamp(x) for x in start_time[0:len(pd_df)] if datetime.datetime.utcfromtimestamp(x).hour==hr]
    bool_vec = [d.hour==hr for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

# return observations within a period of 2 specified days (first and last days must be unix time stamps: datetime.strptime('2015-10-20 22:24:46', '%Y-%m-%d %H:%M:%S') )
def obs_in_days(firstday,lastday,pd_df):
    start_time = [pd_df['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(pd_df))]
    vec=[datetime.datetime.utcfromtimestamp(x) for x in start_time[0:len(pd_df)] if ((datetime.datetime.utcfromtimestamp(x)<= firstday) & (datetime.datetime.utcfromtimestamp(x)>=lastday))]
    bool_vec = [((datetime.datetime.utcfromtimestamp(d) >=firstday) & (datetime.datetime.utcfromtimestamp(d)<= lastday)) for d in start_time]
    return pd_df.loc[bool_vec].reset_index()

# extracts the days of each trip
def get_days_of_trips(tripsdf): # for plotting trips per day of week
    start_time = [tripsdf['route'][i]['features'][0]['properties']['timestamp'] for i in range(len(tripsdf))]
    return [calendar.day_name[datetime.datetime.utcfromtimestamp(x).weekday()] for x in start_time]

# counts the frequency of each day given vector of days
def count_days(day,dayvec): # for plotting trips per day of week
    vec=[dayvec[i]==day for i in range(len(dayvec))]
    return sum(vec)

# returns plots for trip taken per day of week
def plot_trips_per_weekdays_for_interval(firstday,lastday,tdb ):

    trips_df = obs_in_days(firstday ,lastday , tdb)
    #trips_df=trips_df.reset_index()
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
             #"hoverinfo":"label+value",
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
             #"hoverinfo":"value",
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

# get urls of images for trips per day
pie_plot_url = py.plot(pie_fig, filename='trips_per_weekdayPie', auto_open=False,)
bar_plot_url = py.plot(bar_fig, filename='trips_per_weekdayBar', auto_open=False,)
double_plot_url = py.plot(double_bar_fig, filename='trips_per_weekdayDoubleBar', auto_open=False,)

def to_twelve_hour(hour): # used for plotting trips per hour
    if hour > 12:
        new=hour-12
        return str(new)+'PM'
    elif hour == 12:
        return str(hour)+ 'PM'
    elif hour == 0:
        return str(12)+ 'AM'
    else:
        return str(hour)+'AM'

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
    'tickangle':'45',
    }
    layout.xaxis=dict(title= "Hour of Day",tickmode='linear')
    layout.plot_bgcolor='rgb(11, 0, 0)'
    hours_fig=go.Figure(data=data,layout=layout)
    return hours_fig

# can filter tdb using obs_in functions for window specification
tdb_filtered = obs_in_days(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 10, 8, 33, 13),tdb)
hours_fig = plot_trips_per_hour(tdb_filtered)
hours_plot_url = py.plot(hours_fig, filename='trips_per_hour', auto_open=False,)

# create map of start points of trips
# create dataframes for startpoints and endpoints with lat and long coords

'''
start_d = {'lat':[], 'lon':[]}
end_d = {'lat':[], 'lon':[]}

end_points = [tdb['route'][i]['features'][1]['geometry']['coordinates'] for i in range(len(tdb))]
start_points = [tdb['route'][i]['features'][0]['geometry']['coordinates'] for i in range(len(tdb))]

for start_p,end_p in zip(start_points,end_points):
    start_lon,start_lat,end_lon, end_lat = start_p[0],start_p[1],end_p[0],end_p[1]
    start_d['lat'].append(start_lat)
    start_d['lon'].append(start_lon)
    end_d['lat'].append(end_lat)
    end_d['lon'].append(end_lon)

startdb = pandas.DataFrame.from_dict(start_d) # db is just lat and long points
enddb = pandas.DataFrame.from_dict(end_d) # db is just lat and long points

# Must be a public token, starting with `pk`
token = os.getenv('MAPBOX_TOKEN')

# Create a geojson file export from a Pandas dataframe
df_to_geojson(startdb, filename='points.geojson',lat='lat', lon='lon')

#Create a heatmap
heatmap_color_stops = create_color_stops([0.01,0.25,0.5,0.75,1], colors='RdPu')
heatmap_radius_stops = [[0,1], [15, 40]] #increase radius with zoom

color_breaks = [0,10,100,1000,10000]
color_stops = create_color_stops(color_breaks, colors='Spectral')

heatmap_weight_stops = create_weight_stops(color_breaks)

#Create a heatmap
viz = HeatmapViz('points.geojson',
                 access_token=token,
                 weight_stops = heatmap_weight_stops,
                 color_stops = heatmap_color_stops,
                 radius_stops = heatmap_radius_stops,
                 opacity = 0.9,
                 center = (-118, 34),
                 zoom = 3,
                 )

x=viz.show()

'''


# configure the html with all plots
html_string = '''
    <html>
    <!-- *** Section 1 *** --->
    
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + pie_plot_url + '''.embed?width=800&height=550"></iframe>
        
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + bar_plot_url + '''.embed?width=800&height=550"></iframe>
        
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + double_plot_url + '''.embed?width=800&height=550"></iframe>
        
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + hours_plot_url + '''.embed?width=900&height=550"></iframe>
            
            
        </body>
    </html>'''

print('Generating \'dash_testing.html\' ...')
f = open('dash_testing.html','w')
f.write(html_string)
f.close()
print('Done.')


