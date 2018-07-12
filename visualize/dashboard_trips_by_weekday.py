
'''
    This file will generate an html file to serve as a precursor for a dashboard file.
    Current visuals: trips per day of week (pie chart, bar plot, grouped bar plot)
    
    
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

con = connect("hannah1ross","password","transit")
tdb, scdb = get_data(con)

def obs_in_month(month,pd_df):
    mo = month
    vec=[datetime.datetime.utcfromtimestamp(x) for x in pd_df.start_time[0:len(pd_df)] if datetime.datetime.utcfromtimestamp(x).month==mo]
    bool_vec = [d.month==mo for d in pd_df['start_time']]
    return pd_df.loc[bool_vec]

def obs_in_hour(hour,pd_df):
    hr = hour
    vec=[datetime.datetime.utcfromtimestamp(x) for x in pd_df.start_time[0:len(pd_df)] if datetime.datetime.utcfromtimestamp(x).hour==hr]
    bool_vec = [d.hour==hr for d in pd_df['start_time']]
    return pd_df.loc[bool_vec]

# first and last days must be unix time stamps    datetime.strptime('2015-10-20 22:24:46', '%Y-%m-%d %H:%M:%S')
def obs_in_days(firstday,lastday,pd_df):
    vec=[datetime.datetime.utcfromtimestamp(x) for x in pd_df.start_time[0:len(pd_df)] if ((datetime.datetime.utcfromtimestamp(x)<= firstday) & (datetime.datetime.utcfromtimestamp(x)>=lastday))]
    bool_vec = [((datetime.datetime.utcfromtimestamp(d) >=firstday) & (datetime.datetime.utcfromtimestamp(d)<= lastday)) for d in pd_df['start_time']]
    return pd_df.loc[bool_vec]


def get_days_of_trips(tripsdf):
    return [calendar.day_name[datetime.datetime.utcfromtimestamp(x).weekday()] for x in tripsdf.start_time[0:len(tripsdf)]]


def count_days(day,dayvec):
    vec=[dayvec[i]==day for i in range(len(dayvec))]
    return sum(vec)

def plot_trips_per_weekdays_for_interval(firstday,lastday,tdb ):
    
    #(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 4, 8, 33, 13) , tdb)
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
    #import plotly.plotly as py
    
    pie_fig = {
        "data": [
                 {
                 "values": [mon_count,tues_count,wed_count,thurs_count,fri_count,sat_count,sun_count ],
                 "labels": [x for x in calendar.day_name],
                 #"name": "Company Ridership",
                 "hoverinfo":"label+value",
                 "type": "pie"
                 },
                 ],
            "layout": {
            "title":"Trips per Day of Week from {}".format(the_interval),
            }
        }
    bar_fig = {
    "data": [
             {
             "y": [mon_count,tues_count,wed_count,thurs_count,fri_count,sat_count,sun_count ],
             "x": [x for x in calendar.day_name],
             #"name": "Company Ridership",
             "hoverinfo":"value",
             "type": "bar"
             },
             ],
        "layout": {
            "title":"Trips per Day of Week from {}".format(the_interval),
            "yaxis":{"title":"Number of Trips"}
            }
            }
             #trips_df = obs_in_days(firstday ,lastday , tdb)
#the_interval = calendar.month_name[firstday.month] +' ' +str(firstday.day)+ ' to '+ calendar.month_name[lastday.month] +' ' +str(lastday.day)

    bat_trips_df = trips_df.loc[trips_df['company_name']=='Bat']
    lemon_trips_df = trips_df.loc[trips_df['company_name']=='Lemon']

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
                       title="Trips per Day of Week from {}".format(the_interval),
                       yaxis={"title":"Number of Trips"}
                       )
        
                       double_bar_fig = go.Figure(data=data, layout=layout)
                       #py.iplot(double_bar_fig, filename='grouped-bar_trips')
                       
                       
    return pie_fig,bar_fig,double_bar_fig

#py.iplot(fig, filename='trips_per_day')

pie_fig,bar_fig,double_bar_fig = plot_trips_per_weekdays_for_interval(datetime.datetime(2018, 8, 3, 8, 32, 13) ,datetime.datetime(2018, 8, 10, 8, 33, 13),tdb )
#py.iplot(result_fig,filename='trips_per_day') # this generates plot inline

pie_plot_url = py.plot(pie_fig, filename='trips_per_weekdayPie', auto_open=False,)
bar_plot_url = py.plot(bar_fig, filename='trips_per_weekdayBar', auto_open=False,)
double_plot_url = py.plot(double_bar_fig, filename='trips_per_weekdayDoubleBar', auto_open=False,)
html_string = '''
    <html>
    <!-- *** Section 1 *** --->
    
    <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
    src="''' + pie_plot_url + '''.embed?width=800&height=550"></iframe>
        
        <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
        src="''' + bar_plot_url + '''.embed?width=800&height=550"></iframe>
            <iframe width="1000" height="550" frameborder="0" seamless="seamless" scrolling="no" \
            src="''' + double_plot_url + '''.embed?width=800&height=550"></iframe>
                
                </body>
                </html>'''

print('Generating \'dash_testing.html\' ...')
f = open('dash_testing.html','w')
f.write(html_string)
f.close()
print('Done.')

