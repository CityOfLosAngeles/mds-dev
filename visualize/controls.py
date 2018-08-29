#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File to be used in dash_app.py and generate_dashboard.py

Update controls as needed to account for modular variables like the names of companies permited to operate, 
and enumerations for vehicle types.


Author : Hannah Ross
"""

# provide a plotly account username and api_key
SETS = {'username':'hannahross33','api_key':'8YSEgJklJCdTJv4u9UIv'}

# update with companies permited to operate 
COMPANIES = {
    '0': 'Bat',
    '1': 'Lemon',
    }

# update with current vehicle_type (device_type) enumerations
VEHICLES = {
    '0': 'scooter',
    '1': 'bike',
}
