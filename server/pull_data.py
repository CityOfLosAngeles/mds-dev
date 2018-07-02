import psycopg2
import pandas
import sqlalchemy
import json
import requests

def connect(user,password,db,host='localhost',port=5432):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

def get_data(con):
    trips_db = pandas.read_sql('SELECT * FROM "trips"',con,index_col=None)
    availability_db = pandas.read_sql('SELECT * FROM "availability"',con,
            index_col=None)
    return (trips_db,availability_db)

con = connect("david","password","transit")
tdb, adb = get_data(con)
print(tdb)
