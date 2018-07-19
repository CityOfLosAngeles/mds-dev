'''
This script generates an html file 'dash_testing.html' of dashboard visualizations for the trips and status_change data.
    
Name and Password fields will need to be changed for 'connect' to read in data from the server.
    
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
import fiona
import shapely.wkt
import shapely.geometry
import sqlalchemy
import pyproj

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

# read in trips and status_change data from the server
con = connect("hannah1ross","password","transit")
tdb, scdb = get_data(con)

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

# get urls of images for trips per day
print "Building plot: 1"
pie_plot_url = py.plot(pie_fig, filename='trips_per_weekdayPie', auto_open=False,)
print "Building plot: 2"
bar_plot_url = py.plot(bar_fig, filename='trips_per_weekdayBar', auto_open=False,)
print "Building plot: 3"
double_plot_url = py.plot(double_bar_fig, filename='trips_per_weekdayDoubleBar', auto_open=False,)

# used for plotting trips per hour
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
    'tickangle':'45',
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
for i in range(12):
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
    # count the number of trips beginning in each dc
    for i in range(12):
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
                    x= [x+1 for x in range(12)],
                    name='Bat'
                    )

    trace2 = go.Bar(
                y=[count for count in lemon_dc_counts ],
                x= [x+1 for x in range(12)],
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
    return py.plot(trips_per_cd_fig,filename='trips_per_cd', auto_open=False,)

print "Building plot: 6"
trips_per_cd_plot_url = plot_trips_per_cd(tdb)


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


# configure the html with all plot urls
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
            
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + company_plot_url + '''.embed?width=900&height=550"></iframe>
            
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="yes" \
            src="''' + trips_per_cd_plot_url + '''.embed?width=900&height=550"></iframe>
                
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="yes" \
                src="''' + availability_pie_url + '''.embed?width=900&height=550"></iframe>
        
            
            </html>
 '''

print('Generating \'dash_testing.html\' ...')
f = open('dash_testing.html','w')
f.write(html_string)
f.close()
print('Done.')


