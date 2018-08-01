CREATE TYPE area AS ENUM ('san_fernando', 'non_san_fernando', 'los_angeles');

CREATE TABLE IF NOT EXISTS equity (
	company_name TEXT NOT NULL,
	device_type TEXT NOT NULL,
	area area NOT NULL,
	start_time BIGINT NOT NULL,
	end_time BIGINT NOT NULL,
	equity_count INT NOT NULL
)
