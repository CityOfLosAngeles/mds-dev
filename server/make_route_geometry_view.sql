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
json_split
