import psycopg2
import pandas
import sqlalchemy
import json
import requests

'''
Script requires a configured environmental variable called DATABASE_URL 

where DATABASE_URL = postgres://user:password@localhost/databasename

    user: SQL server username
    password: SQL server password
    databasename: SQL server database name
'''
def get_data(con):
    trips_db = pandas.read_sql('SELECT * FROM "trips"',con,index_col=None)
    status_change_db = pandas.read_sql('SELECT * FROM "status_change"',con,
            index_col=None)
    return (trips_db,status_change_db)

# using environmental variables
DATABASE_URL = os.environ['DATABASE_URL']
con = psycopg2.connect(DATABASE_URL)

tdb, scdb = get_data(con)
print(tdb)
print(scdb)
