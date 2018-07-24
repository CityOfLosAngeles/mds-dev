"""
A short python script to check if the available bikes are meeting equity
measures.

Get the title? It's a pun.

Written by: David Klinger
"""

import argparse
import sqlalchemy
import psycopg2
import pandas
import fiona
import pyproj
import shapely.geometry
import shapely.ops
import pprint

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
args = parser.parse_args()

def connect(user, password, db, host, port):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

def chequity(db, start_area, end_area):
    None

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



user = args.user
password = args.password
db = args.database
host = "localhost"
if args.host is not None:
    host = args.host
port = 5432
if args.port is not None:
    port = args.port
con = connect(user,password,db,host,port)

city_boundary = read_area('City_Boundary.shp')
sf_equity = read_area('San_Fernando_Valley.shp')
non_sf_equity = read_area('Non_San_Fernando.shp')

"""
print(city_boundary)
print(sf_equity)
print(non_sf_equity)
"""

# avail_db = pandas.read_sql('SELECT * FROM "availability"',con,index_col=None)
