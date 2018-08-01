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
import time
import datetime
import sortedcontainers

# set up required command line arguments
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

# connect to database
def connect(user, password, db, host, port):
    url = 'postgresql://{}:{}@{}:{}/{}'
    url = url.format(user,password,host,port,db)
    con = sqlalchemy.create_engine(url)
    return con

# class to hold information on intervals, as keys
class interval:
    
    # specification: one interval holds a start and end time
    # in seconds, unix std time
    def __init__(self,start,end):
        self.start = start
        self.end = end

    # comparison ops only defined on start time
    # to avoid weird behavior with bisect_right
    def __lt__(self,interval):
        return self.start < interval.start
    
    def __eq__(self, interval):
        return self.start == interval.start

    def __str__(self):
        return "({}, {})".format(self.start,self.end)

    def __repr__(self):
        return "({}, {})".format(self.start,self.end)

    def __hash__(self):
        return hash(self.__repr__())


# class to hold and edit intervals of time
# each interval maps to a # of vehicles available
class intervals:

    def __init__(self,start,end):
        self.counts = sortedcontainers.SortedDict()
        i = interval(int(start),int(end))
        self.counts[i] = 0

    def add_interval(self,t_s,t_e):
        i = self.counts.bisect_right(interval(t_s,t_e))-1
        if i<0:
            i = 0
        to_remove = sortedcontainers.SortedSet()
        to_add = sortedcontainers.SortedDict()
        while i < len(self.counts) and self.counts.keys()[i].start < t_e:
            key = self.counts.keys()[i]
            s = key.start
            e = key.end
            cnt = self.counts[key]
            if t_s <= s and t_e >= e:
                to_add[interval(s,e)] = cnt+1
            elif t_s <= s and t_e > s and t_e < e:
                to_remove.add(key)
                to_add[interval(s,t_e)] = cnt+1
                to_add[interval(t_e,e)] = cnt
            elif t_s > s and t_s < e and t_e >= e:
                to_remove.add(key)
                to_add[interval(s,t_s)] = cnt
                to_add[interval(t_s,e)] = cnt+1
            elif t_s > s and t_e < e:
                to_remove.add(key)
                to_add[interval(s,t_s)] = cnt
                to_add[interval(t_s,t_e)] = cnt+1
                to_add[interval(t_e,e)] = cnt
            i += 1

        for r in to_remove:
            self.counts.pop(r)
        for k in to_add.keys():
            self.counts[k] = to_add[k]


def chequity(con, start, end, area, company, device):
    command = """
              SELECT * FROM "availability" 
              WHERE ((start_time < {} AND end_time > {}) OR
                     (start_time < {} AND end_time > {}) OR
                     (start_time > {} AND end_time < {})) AND
                     company_name = '{}' AND
                     device_type = '{}'
              ORDER BY start_time, end_time
              """.format(start, start, end, end, start, end, 
                         company, device)
    db = pandas.read_sql(command,con,index_col=None)
    i_s = intervals(start,end)
    for i,r in db.iterrows():
        if i%500==0:
            print("{} of {}".format(i,len(db)))
        t_s = r['start_time']
        t_e = r['end_time']
        loc = r['location'].strip("()").split(",")
        loc = shapely.geometry.Point(float(loc[0]), float(loc[1]))
        if area.contains(loc):
            i_s.add_interval(t_s,t_e)
    """ 
    for k in i_s.counts.keys():
        print("Looking at key: {}".format(k))
        flag = (k in i_s.counts.keys())
        if not flag:
            print("Key isn't in there!")
        else:
            print("Key maps to {}".format(i_s.counts[k]))
    """
    s = 0
    for k in i_s.counts.keys():
        if k in i_s.counts.keys():
            # sometimes value is removed but not the key itself with pop
            # bug in library?
            s += i_s.counts[k]*(k.end-k.start)
    return s/(end-start)


    """
    # Old code, left in for posterity
    # also in case the new code is horribly wrong
    intervals = set()
    for i,r in db.iterrows():
            new_interval = set()
            while len(interval) > 0:
                s,e,cnt = interval.pop()
                to_add = []
                if t_s <= s and t_e > s and t_e < e:
                    to_add = [(s,t_e,cnt+1),(t_e,e,cnt)]
                elif t_s > s and t_s < e and t_e >= e:
                    to_add = [(s,t_s,cnt),(t_s,e,cnt+1)]
                elif t_s <= s and t_e >= e:
                    to_add = [(s,e,cnt+1)]
                elif t_s > s and t_e < e:
                    to_add = [(s,t_s,cnt),(t_s,t_e,cnt+1),(t_e,e,cnt)]
                else:
                    to_add = [(s,e,cnt)]
                new_interval.update(to_add)
            interval = new_interval
    print(interval)
    """

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

for i in range(0,31):
    start = time.mktime(datetime.datetime(2018,8,i+1,0,0,0).timetuple())
    end = start + 24*60*60
    company = ["Bat", "Lemon"]
    areas = [("san_fernando",sf_equity),("non_san_fernando",non_sf_equity),
             ("los_angeles",city_boundary)]
    print("Day {}".format(i))
    for c in company:
        print("Company {}".format(c))
        for n,a in areas:
            print("Area {}".format(n))
            avg= chequity(con,start,end,a,c,"scooter")
            con.execute("INSERT INTO equity VALUES ('{}', 'scooter','{}',{},{},{})".
                    format(c,n,start,end,avg))

    
