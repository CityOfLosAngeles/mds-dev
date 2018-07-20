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

CREATE VIEW availability AS

WITH cte AS (
	WITH no_repeat_table AS (
		WITH repeat_table AS (
			WITH row_table AS (
				SELECT *, row_number()
				OVER (order by company_name,
					       device_type,
					       device_id,
					       event_time) as row_num
				FROM status_change
			)

			SELECT
			i.company_name AS company_name,
			i.device_type AS device_type,
			i.device_id AS device_id,
			i.event_type AS event_type,
			i.reason AS reason,
			i.event_time AS event_time,
			i.location AS location,
			i.battery_pct AS battery_pct,
			i.associated_trips AS associated_trips,
			i.row_num AS row_num,
			(j.row_num IS NULL) AS condition

			FROM
			row_table AS i LEFT JOIN row_table as j
			ON i.row_num-1=j.row_num AND
				((i.event_type='available' AND j.event_type='available') OR
				(i.event_type<>'available' AND j.event_type<>'available'))

		)

		SELECT

		company_name,
		device_type,
		device_id,
		event_type,
		reason,
		event_time,
		location,
		battery_pct,
		associated_trips

		FROM

		repeat_table

		WHERE

		condition
	)
	SELECT

	company_name,
	device_type,
	device_id,
	event_type,
	reason,
	event_time,
	location,
	battery_pct,
	associated_trips,
	row_number() OVER() as n

	FROM no_repeat_table
)

SELECT

a.company_name,
b.device_type,
a.device_id,
a.event_type AS start_event_type,
b.event_type AS end_event_type,
a.location,
a.reason AS start_reason,


b.reason AS  end_reason,
a.event_time AS start_time,
b.event_time AS end_time


FROM
cte AS a INNER JOIN cte AS b
ON a.n+1 = b.n
WHERE a.event_type = 'available' and b.event_type <> 'available';

CREATE VIEW route_geometry AS

WITH json_split AS (

	SELECT

	company_name,
	device_type,
	device_id,
	trip_duration,
	trip_distance,
	accuracy,
	json_array_elements(route->'features') AS loc,
	trip_id,
	parking_verification,
	standard_cost,
	actual_cost

	FROM

	trips
)

SELECT

company_name,
device_type,
device_id,
trip_duration,
trip_distance,
accuracy,
((loc->'properties')->'timestamp') AS timestamp,
ST_AsText(ST_GeomFromGeoJSON((loc->'geometry')::text)) as location,
trip_id,
parking_verification,
standard_cost,
actual_cost

FROM
json_split;

