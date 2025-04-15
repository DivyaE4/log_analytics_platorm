import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, MetaData, Table, select, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()

class Database:
    def __init__(self, host, port, user, password, dbname):
        self.connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        self.engine = create_engine(self.connection_string)
        self.metadata = MetaData()
        self.Session = sessionmaker(bind=self.engine)
        
        # Define tables
        self.api_logs = Table(
            'api_logs', 
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('request_id', String),
            Column('endpoint', String),
            Column('method', String),
            Column('status_code', Integer),
            Column('response_time_ms', Float),
            Column('user_agent', String),
            Column('timestamp', DateTime)
        )
        
        self.error_logs = Table(
            'error_logs', 
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('request_id', String),
            Column('endpoint', String),
            Column('method', String),
            Column('status_code', Integer),
            Column('response_time_ms', Float),
            Column('user_agent', String),
            Column('timestamp', DateTime),
            Column('error_message', String)
        )
        
        # Define aggregate tables for analytics
        self.endpoint_stats = Table(
            'endpoint_stats', 
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('endpoint', String),
            Column('method', String),
            Column('count', Integer),
            Column('avg_response_time', Float),
            Column('min_response_time', Float),
            Column('max_response_time', Float),
            Column('error_count', Integer),
            Column('time_window', String),  # '5min', '1hour', '1day'
            Column('timestamp', DateTime)
        )
        
        self.error_stats = Table(
            'error_stats', 
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('status_code', Integer),
            Column('count', Integer), 
            Column('time_window', String),
            Column('timestamp', DateTime)
        )
    
    def setup(self):
        """Create tables if they don't exist"""
        try:
            self.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
            
            # Create stored procedures for aggregations
            with self.engine.connect() as conn:
                # Function to update endpoint stats every 5 minutes
                conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_endpoint_stats()
                RETURNS VOID AS $$
                BEGIN
                    -- 5 minute stats
                    INSERT INTO endpoint_stats (endpoint, method, count, avg_response_time, min_response_time, max_response_time, error_count, time_window, timestamp)
                    SELECT 
                        endpoint, 
                        method, 
                        COUNT(*) as count, 
                        AVG(response_time_ms) as avg_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time,
                        SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count,
                        '5min' as time_window,
                        date_trunc('minute', NOW()) as timestamp
                    FROM 
                        api_logs
                    WHERE 
                        timestamp > NOW() - INTERVAL '5 minutes'
                    GROUP BY 
                        endpoint, method;
                        
                    -- 1 hour stats
                    INSERT INTO endpoint_stats (endpoint, method, count, avg_response_time, min_response_time, max_response_time, error_count, time_window, timestamp)
                    SELECT 
                        endpoint, 
                        method, 
                        COUNT(*) as count, 
                        AVG(response_time_ms) as avg_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time,
                        SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count,
                        '1hour' as time_window,
                        date_trunc('hour', NOW()) as timestamp
                    FROM 
                        api_logs
                    WHERE 
                        timestamp > NOW() - INTERVAL '1 hour'
                    GROUP BY 
                        endpoint, method;
                END;
                $$ LANGUAGE plpgsql;
                """))
                
                # Function to update error stats
                conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_error_stats()
                RETURNS VOID AS $$
                BEGIN
                    -- 5 minute error stats
                    INSERT INTO error_stats (status_code, count, time_window, timestamp)
                    SELECT 
                        status_code, 
                        COUNT(*) as count,
                        '5min' as time_window,
                        date_trunc('minute', NOW()) as timestamp
                    FROM 
                        api_logs
                    WHERE 
                        status_code >= 400 AND
                        timestamp > NOW() - INTERVAL '5 minutes'
                    GROUP BY 
                        status_code;
                        
                    -- 1 hour error stats
                    INSERT INTO error_stats (status_code, count, time_window, timestamp)
                    SELECT 
                        status_code, 
                        COUNT(*) as count,
                        '1hour' as time_window,
                        date_trunc('hour', NOW()) as timestamp
                    FROM 
                        api_logs
                    WHERE 
                        status_code >= 400 AND
                        timestamp > NOW() - INTERVAL '1 hour'
                    GROUP BY 
                        status_code;
                END;
                $$ LANGUAGE plpgsql;
                """))
                
                logger.info("Database stored procedures created successfully")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
    
    def insert_api_log(self, log_data):
        """Insert a new API log"""
        try:
            with self.engine.connect() as conn:
                # Convert string timestamp to datetime
                timestamp = datetime.datetime.strptime(log_data.get('timestamp'), "%Y-%m-%d %H:%M:%S")
                
                conn.execute(self.api_logs.insert().values(
                    request_id=log_data.get('request_id'),
                    endpoint=log_data.get('endpoint'),
                    method=log_data.get('method'),
                    status_code=log_data.get('status_code'),
                    response_time_ms=log_data.get('response_time_ms'),
                    user_agent=log_data.get('user_agent'),
                    timestamp=timestamp
                ))
                return True
        except Exception as e:
            logger.error(f"Error inserting API log: {e}")
            return False
    
    def insert_error_log(self, log_data):
        """Insert a new error log"""
        try:
            with self.engine.connect() as conn:
                # Convert string timestamp to datetime
                timestamp = datetime.datetime.strptime(log_data.get('timestamp'), "%Y-%m-%d %H:%M:%S")
                
                conn.execute(self.error_logs.insert().values(
                    request_id=log_data.get('request_id'),
                    endpoint=log_data.get('endpoint'),
                    method=log_data.get('method'),
                    status_code=log_data.get('status_code'),
                    response_time_ms=log_data.get('response_time_ms'),
                    user_agent=log_data.get('user_agent'),
                    timestamp=timestamp,
                    error_message=log_data.get('error_message', '')
                ))
                return True
        except Exception as e:
            logger.error(f"Error inserting error log: {e}")
            return False
    
    def update_stats(self):
        """Update statistics tables"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT update_endpoint_stats()"))
                conn.execute(text("SELECT update_error_stats()"))
                return True
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
            return False
    
    def close(self):
        """Close the database connection"""
        self.engine.dispose()