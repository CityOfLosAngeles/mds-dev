/*
I'm sorry you have to read this
*/

CREATE VIEW availability AS 

WITH full_table AS (
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
				   i.device_id=j.device_id AND
					((i.event_type='available' AND 
					  j.event_type='available') OR
					(i.event_type<>'available' AND 
			 		 j.event_type<>'available'))

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
	), 

	trip_rows AS (
		SELECT *, 
		row_number() OVER (order by company_name,
			       		    device_type,
			       		    device_id,
			       		    event_time) as row_num
		FROM status_change
	)

	SELECT

	a.company_name,
	a.device_type,
	a.device_id,
	ST_ASTEXT(ST_POINT(a.location[0],a.location[1])) AS location,
	a.event_type AS start_event_type,
	b.event_type AS end_event_type,
	a.reason AS start_reason,


	b.reason AS  end_reason,
	a.event_time AS start_time,
	b.event_time AS end_time

	FROM
	cte AS a LEFT JOIN cte AS b
	ON a.event_type = 'available' AND b.event_type <> 'available' AND 
	   a.device_id = b.device_id AND
	   a.n+1 = b.n

	WHERE
	a.event_type = 'available'

	UNION 

	SELECT

	c.company_name,
	c.device_type,
	c.device_id,
	ST_ASTEXT(ST_POINT(c.location[0],c.location[1])) AS location,
	c.event_type AS start_event_type,
	d.event_type AS end_event_type,
	c.reason AS start_reason,

	d.reason AS end_reason,
	c.event_time AS start_time,
	d.event_time AS end_time

	FROM 
	trip_rows AS c LEFT JOIN trip_rows AS d
	ON c.reason = 'user_pick_up' AND
	   c.device_id = d.device_id AND
	   c.row_num+1 = d.row_num

	WHERE c.reason = 'user_pick_up'

)

SELECT *
FROM full_table
ORDER BY (start_time, company_name, device_type, device_id)
