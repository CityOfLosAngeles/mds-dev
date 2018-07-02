CREATE TABLE IF NOT EXISTS trips (
    company_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    trip_id UUID NOT NULL,
    trip_duration INT NOT NULL,
    trip_distance INT NOT NULL,
    start_point POINT NOT NULL,
    end_point POINT NOT NULL,
    accuracy INT NOT NULL,
    route LINE,
    sample_rate INT,
    device_id UUID NOT NULL,
    start_time BIGINT NOT NULL,
    end_time BIGINT NOT NULL,
    parking_verification TEXT NOT NULL,
    standard_cost INT,
    actual_cost INT
);

CREATE TYPE placement_reason AS ENUM ('user_drop_off',
        'rebalancing_drop_off',
        'maintenance_drop_off',
	'out_of_service_area_drop_off');

CREATE TYPE pickup_reason AS ENUM ('user_pick_up',
        'out_of_service_area_pick_up',
	'maintenance_pick_up');

CREATE TABLE IF NOT EXISTS availability (
    company_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_id UUID NOT NULL,
    availability_start_time BIGINT NOT NULL,
    availability_end_time BIGINT NOT NULL,
    placement_reason placement_reason NOT NULL,
    allowed_placement BOOLEAN NOT NULL,
    pickup_reason pickup_reason NOT NULL,
    associated_trips UUID[]
);




