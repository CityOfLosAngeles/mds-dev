`chequity.py` is a python script that contains code to check the average number of available vehicles for a given time frame, company, and vehicle type.

Before running it make sure that the status change table is filled and the availability table is working (see `mds-dev/server`). Run `psql [db-name] -f make_equity_table.sql` to make the equity table. 

To fill the equity table by checking equity, use the following command line option:

`chequity.py user password database`. 

It automatically runs over the fake data generated in `mds-dev/data`, running through each day and each company and each area. It takes over an hour to run on my computer. 

