## Creating Dashboard

`generate_dashboard.py` is a short python script to generate an html file with basic MDS visualizations. The visualizations are not interactive. 

`controls.py` is a script used in `dash_app.py` containing relevant plotly settings and relevant enumerations for vehicle_type and company_name. Enumerations should be updated with any new vehicle types and company names to come from the real data.

`dash_app.py` is a long python script to generate a locally hosted plotly Dash application for the MDS dashboard. This script imports SETS, COMPANIES, and VEHICLES from `controls.py`.


See comments in `dash_app.py` for detailed information on how to run the script for real data vs for the mock API data

## Usage

`python dash_app.py [username] [password] [database name]` will run a locally hosted dash application
where [username] and [password] are for a Postgres SQL server and [database name] is the name of the database 

`python generate_dashboard.py [username] [password] [database name]` will create a local html file called 'dash_testing.html' with basic plots that do not take user given parameters
