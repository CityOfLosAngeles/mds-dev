import psycopg2
import json
import pprint
import requests

conn = None
try:
    conn = psycopg2.connect("dbname='transit'")
    cur = conn.cursor()

    try:
        cur.execute('DROP TABLE "trips";')
        print("Successfully dropped table trips.")
    except:
        print("Could not drop table trips, does not exist.")
    try: 
        cur.execute('DROP TABLE "availability";')
        print("Successfully dropped table availability.")
    except:
        print("Could not drop table availability, does not exist.")
    try:
        cur.execute('DROP TYPE "pickup_reason";')
        print("Successfully dropped type pickup_reason.")
    except:
        print("Could not drop type pickup_reason, does not exist.")
    try:
        cur.execute('DROP TYPE "placement_reason";')
        print("Successfully dropped type placement_reason.")
    except:
        print("Could not drop type placement_reason, does not exist.")
    conn.commit()

except (Exception, psycopg2.DatabaseError) as error:
    print(error)
finally:
    if conn is not None:
        conn.close()
