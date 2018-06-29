import psycopg2
import json
import pprint
import requests

def create_trip_table():
    conn = None
    try:
        conn = psycopg2.connect("dbname='transit'")
        cur = conn.cursor()
        cur.execute("""select exists(select * from information_schema.tables 
                       where table_name=%s)""", ('trips',))
        if cur.fetchone()[0]:
            print("Error: trips table already exists.")
            return
        make_database = """
                        CREATE table trips (
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
                        )
                        """
        cur.execute(make_database)
        conn.commit()
        print("Success.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

def create_availability_table():
    conn = None
    try:
        conn = psycopg2.connect("dbname='transit'")
        cur = conn.cursor()
        cur.execute("""select exists(select * from information_schema.tables 
                       where table_name=%s)""", ('availability',))
        if cur.fetchone()[0]:
            print("Error: availability table already exists.")
            return
        make_database = ["""
                        CREATE TYPE placement_reason AS ENUM ('user_drop_off',
                                'rebalancing_drop_off',
                                'maintenance_drop_off',
                                'out_of_service_area_drop_off')
                        """,
                        """
                        CREATE TYPE pickup_reason AS ENUM ('user_pick_up',
                                'out_of_service_area_pick_up',
                                'maintenance_pick_up')
                        """,
                        """
                        CREATE table availability (
                            company_name TEXT NOT NULL,
                            device_type TEXT NOT NULL,
                            device_id UUID NOT NULL,
                            availability_start_time BIGINT NOT NULL,
                            availability_end_time BIGINT NOT NULL,
                            placement_reason placement_reason NOT NULL,
                            allowed_placement BOOLEAN NOT NULL,
                            pickup_reason pickup_reason NOT NULL,
                            associated_trips UUID[]
                        )
                        """]
        for c in make_database:
            cur.execute(c)
        conn.commit()
        print("Success.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

create_trip_table()
create_availability_table()
