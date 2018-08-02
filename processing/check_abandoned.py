"""
Short script to send alerts

Usage: python check_abandoned.py source_email target_email user pass database

Note passwords can be piped in:
    echo "pass" | python check_abandoned.py source_email target_email user pass database

I won't pretend to know enough about security to know how to do this securely, but 
this can be automated. 

NOTE: If the email is sent to a gmail account, you MUST allow less secure apps.
Link to setting - https://myaccount.google.com/lesssecureapps

ADDITIONAL NOTE: To use on fake data, I have made the current time Sep 2nd, 2018 at noon.
Change this to the actual current time when using this on real data!

"""

import argparse
import getpass
import sys
import smtplib
from email.message import EmailMessage
import time
import pandas
import sqlalchemy
from ast import literal_eval
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("source_email",type=str,
        help="email that the alert will be sent from")
parser.add_argument("target_email",type=str,
        help="email to send the alert to")
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


# CHANGE THIS VALUE
current_time = datetime(2018,9,2,12,0,0,0)
current_timestamp = time.mktime(current_time.timetuple())

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

db = pandas.read_sql("SELECT * FROM availability WHERE end_time IS NULL", 
        con, index_col=None)

offending_vehicles = []

for i,row in db.iterrows():
    time_elapsed = int(current_timestamp-row['start_time'])
    days = time_elapsed // (24*60*60)
    if days > 0:
        time_elapsed %= (24*60*60)
        hours = time_elapsed // (60*60)
        time_elapsed %= (60*60)
        minutes = time_elapsed // 60
        time_elapsed %= 60
        seconds = time_elapsed
        elapsed_message = ""
        if days > 1:
            elapsed_message += "{} days, ".format(days)
        elif days == 1:
            elapsed_message += "{} day, ".format(days)
        if hours > 1:
            elapsed_message += "{} hours, ".format(hours)
        elif hours == 1:
            elapsed_message += "{} hour, ".format(hours)
        if minutes > 1:
            elapsed_message += "{} minutes, ".format(minutes)
        elif minutes == 1:
            elapsed_message += "{} minute, ".format(minutes)
        if seconds > 1 or seconds == 0:
            elapsed_message += "and {} seconds".format(seconds)
        elif seconds == 1:
            elapsed_message += "and 1 second".format(seconds)
        message = ""
        message += "{} {}".format(row['company_name'],
                                  row['device_type'])
        message += "\nID: {}".format(row['device_id'])
        message += "\nHas not been moved for: {}".format(elapsed_message)
        message += "\nAvailable since: {}".format(
                datetime.fromtimestamp(int(row['start_time'])))
        x,y = literal_eval(row['location'])
        message += "\nLocation: "
        message += "https://www.google.com/maps?q={},{}".format(y,x)
        offending_vehicles.append(message)

msg = EmailMessage()
message = "{} vehicles have been on the street for over 24 hours without moving.".format(
        len(offending_vehicles))
message+="\n\n"
for ov in offending_vehicles:
    message += ov
    message += "\n\n"
msg.set_content(message)
msg['Subject'] = "[MDS Alert] Potentially Abandoned Vehicles at {}".format(current_time)
msg['From'] = args.source_email
msg['To'] = args.target_email

password = ""
if sys.stdin.isatty():
    password = getpass.getpass()
else:
    password = sys.stdin.readline().rstrip()

server = smtplib.SMTP('smtp.gmail.com',587)
server.starttls()
server.login(args.source_email,password)
server.send_message(msg)

