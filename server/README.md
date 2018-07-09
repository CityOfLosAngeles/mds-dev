This folder contains a series of scripts useful for creating and maintaining the database. To run the sql scripts, run `psql -d [database] -f [filename]` in the command line. 

`reset.sql` will drop all databases and custom types. Use with caution. Mostly for internal testing. 

`make_tables.sql` will create the trip and status change tables inside of the specified database.

`pull_data.py` pulls from the trip and status change tables from the database and read it into pandas dataframes. To run, use the command `python pull_data.py user password database [--host HOST] [--port PORT]`. The host and port options are optional, and it will default to `localhost:5432`

`fill_tables.py` will fill the tables with json data. To run, use the command `python user passsword database [--host HOST] [--port PORT] filename`. The `filename` must be a path to a file with a list of urls in this format:

```
protocol://trip_url_1, trips
protocol://status_change_url_1, status_change
protocol://trip_url_2, trips
protocol://status_change_url_2, status_change
```
The script with parse that file, pull data from that url and will add it to the given database, supposing the tables have been correctly set up with `make_tables.sql`. 
