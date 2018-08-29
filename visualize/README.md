## Creating the Dockless Dashboard

`generate_dashboard.py` is a short python script to generate an html file `dash_testing.html` with preliminary MDS visualizations. The visualizations are not interactive. 

`controls.py` is a script used in `dash_app.py` containing relevant plotly account settings (SETS) and relevant enumerations for vehicle_type (VEHICLES) and company_name (COMPANIES). Enumerations should be updated with all new vehicle types and/or company names to be coming from the real data.

`dash_app.py` is a long python script to generate a locally hosted plotly Dash application for the MDS dashboard. This script imports SETS, COMPANIES, and VEHICLES from `controls.py`.


See comments atop `dash_app.py` for detailed information on how to run the script for real data vs for the mock API data, and for notes on bugs.

Before running scripts make sure that status change and trips tables are filled and the availability view table is working (see mds-dev/server). 



## Usage

`python dash_app.py [username] [password] [database name]` will run a locally hosted Dash application (currently for the fake data hosted in a Postgres SQL Server) where [username] and [password] are for the Postgres SQL server and [database name] is the name of the database 

`python generate_dashboard.py [username] [password] [database name]` will create a local html file called `dash_testing.html` with preliminary plots.

Update plotly account settings with a new account's information in SETS of `controls.py` to fix issues for exceeding plotly account limits.
