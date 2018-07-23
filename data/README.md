## Generating Data

`generate_data.py` is a short python script to generate json files containing trip, status change, and service area date for two fake scooter companies, Bat and Lemon.

See comments in the file for detailed information on generation but there are a few things to note:

1) The data is well formed

2) Anytime a scooter ends up outside the service area (in this case, Council District 10), it is picked up in up to 2 hours by the company. This may not be realistic.

3) Every night, at about 2 am, all scooters are picked up for charging. They are released at 6 am.

## Usage

`python generate_data.py` will create the csv files. Requires pandas, numpy, fiona, pprint, shapely, pyproj, and datetime. It takes a while to run, but the code goes through four stages: generating data, converting trips to json, and then converting status changes to json. It will output paginated jsons in four folders: `bat_trips/`, `lemon_trips/`, `lemon_status_change/`, and `bat_status_change/`
