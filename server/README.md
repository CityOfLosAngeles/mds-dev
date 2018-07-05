This folder contains a series of scripts useful for creating and maintaining the database. To run the sql scripts, run `psql -d [database] -f [filename]` in the command line. 

`reset.sql` will drop all databases and custom types. Use with caution. Mostly for internal testing. 

`make_tables.sql` will create the trip and status change tables inside of the specified database.

`pull_data.py` pulls from the trip and status change tables from the database and read it into pandas dataframes. To run, use the command `python user password database pull_data.py [--host HOST] [--port PORT]`. The host and port options are optional, and it will default to `localhost:5432`

`fill_tables.py` will fill the tables with json data - currently only working if they are in specific filenames and hosted locally on `localhost:8000`. Use the same command line options as `pull_data.py` to specify the database to connect to. 
