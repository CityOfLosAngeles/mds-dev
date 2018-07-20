CREATE TABLE IF NOT EXISTS trips (
    company_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_id UUID NOT NULL,
    trip_duration INT NOT NULL,
    trip_distance INT NOT NULL,
    route JSON NOT NULL,
    accuracy INT NOT NULL,
    trip_id UUID NOT NULL,
    parking_verification TEXT NOT NULL,
    standard_cost INT,
    actual_cost INT
);

CREATE TYPE event_type AS ENUM ('available',
        'reserved',
        'unavailable',
	'removed');

CREATE TYPE reason AS ENUM ('service_start',
	'maintenance',
	'maintenance_drop_off',
	'rebalance_drop_off',
        'user_drop_off',
	'user_pick_up',
	'low_battery',
	'service_end',
	'rebalance_pick_up',
	'maintenance_pick_up',
	'out_of_service_area_pick_up',
	'out_of_service_area_drop_off');

CREATE TABLE IF NOT EXISTS status_change (
    company_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_id UUID NOT NULL,
    event_type event_type NOT NULL,
    reason reason NOT NULL,
    event_time BIGINT NOT NULL,
    location POINT NOT NULL,
    battery_pct FLOAT NOT NULL,
    associated_trips UUID[]
);


