## Generating Data

`generate_trips.py` is a short python script to generate csv files containing trip and availability date for two fake scooter companies, FlipBird and Lime.

See comments in the file for detailed information on generation but there are a few things to note:

1) The data is well formed

2) Anytime a scooter ends up outside the service area (in this case, Council District 10), it is picked up in up to 2 hours by the company. This may not be realistic.

3) Every night, at about 2 am, all scooters are picked up for charging. They are released at 6 am.

## Usage

`python generate_trips.py` will create the csv files. Requires pandas, numpy, fiona, pprint, pyproj, and datetime. Probably won't run on Windows (sorry).
