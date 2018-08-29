#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Required file to be imported for generate_dashboard.py

File should be updated as needed to account for variables like the name of companies permited to operate, 
plotly credential settings, and shapefile filepaths
- company names
- shapefiles

Author : Hannah Ross
"""
# provide plotly account username and api_key
SETS = {'username':'hannahross33','api_key':'8YSEgJklJCdTJv4u9UIv'}

# provide list of companies permited to operate and included in database
COMPANIES = {
    '0': 'Bat',
    '1': 'Lemon',
    }

VEHICLES = {
    '0': 'scooter',
    '1': 'bike',
}
