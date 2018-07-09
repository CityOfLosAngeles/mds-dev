"""
This file will convert each of the json files from the fake mobility providers (serive_area, status_change, and trips) into csv files.

Author: Hannah Ross
"""

import json
import csv

# converts json files for trips, status change, and service area into csv files
def json_data_to_csv(json_filename, output_csv_filename):
    
    # read in json data
    f = open(json_filename)
    data_parsed = json.load(f)
    f.close()
    
    dev_data = data_parsed['data']

    # open a file for writing
    device_data = open(output_csv_filename, 'w')

    # create the csv writer object
    csvwriter = csv.writer(device_data)

    count = 0
    
    for dev in dev_data:
        if count == 0:
            header = dev.keys()

            csvwriter.writerow(header)

            count += 1

        csvwriter.writerow(dev.values())

    device_data.close()
    
# availability data
print('Creating status_change csv files.')
json_data_to_csv('bat_status_change.json','bat_status_change.csv')
json_data_to_csv('lemon_status_change.json','lemon_status_change.csv')
print('Done.')

# trips data
print('Creating trips csv files.')
json_data_to_csv('bat_trips.json','bat_trips.csv')
json_data_to_csv('lemon_trips.json','lemon_trips.csv')
print('Done.')

# service area data
print('Creating service_area csv files.')
json_data_to_csv('lemon_service_area.json','lemon_service_area.csv')
json_data_to_csv('bat_service_area.json','bat_service_area.csv')
print('Done.')
    

