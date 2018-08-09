`chequity.py` is a python script that contains code to check the average number of available vehicles for a given time frame, company, and vehicle type.

Before running it make sure that the status change table is filled and the availability table is working (see `mds-dev/server`). Run `psql [db-name] -f make_equity_table.sql` to make the equity table. 

To fill the equity table by checking equity, use the following command line option:

`chequity.py user password database`. 

It automatically runs over the fake data generated in `mds-dev/data`, running through each day and each company and each area. It takes over an hour to run on my computer. 

***

`check_abandoned.py` is a short script to check for bikes that haven't been sent for a while and sends an email alert. 

Usage: 1python check_abandoned.py source_email target_email user pass database`

Note passwords can be piped in:
    `echo "pass" | python check_abandoned.py source_email target_email user pass database`

I won't pretend to know enough about security to know how to do this securely, but 
this can be automated. 

NOTE: If the email is sent to a gmail account, you MUST allow less secure apps.
Link to setting - https://myaccount.google.com/lesssecureapps

ADDITIONAL NOTE: To use on fake data, I have made the current time Sep 2nd, 2018 at noon.
Change this to the actual current time when using this on real data!

***

`create_neighborhood_counts.py` is a short script to automate creation of geojson file to visualize neighborhood
level counts of available bikes.

Usage: python create_neighborhood_counts.py user password database

Requires making a directory called neighborhood_counts in the same folder as this file.

Then you can use run `jupyter nbconvert --execute neighborhood_counts/create_html.ipynb` to create an html in this folder that will display the map.

