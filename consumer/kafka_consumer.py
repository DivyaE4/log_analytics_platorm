from kafka import KafkaConsumer
import json
import logging
import threading
import time

logger = logging.getLogger(__name__)

class LogConsumer:
    def __init__(self, bootstrap_servers, topics, group_id, db):
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.group_id = group_id
        self.db = db
        self.consumer = None
        self.running = False
        self.stats_thread = None
    
    def connect(self):
        try:
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset='earliest',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                enable_auto_commit=True,
                auto_commit_interval_ms=5000
            )
            logger.info(f"Connected to Kafka, subscribed to topics: {self.topics}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    def start_consuming(self):
        """Start consuming messages from Kafka"""
        if not self.connect():
            logger.error("Failed to start consumer, could not connect to Kafka")
            return False
        
        self.running = True
        
        # Start a thread to update stats periodically
        self.stats_thread = threading.Thread(target=self.update_stats_periodically)
        self.stats_thread.daemon = True
        self.stats_thread.start()
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                topic = message.topic
                value = message.value
                
                logger.debug(f"Received message from topic {topic}: {value}")
                
                if topic == 'api-requests':
                    self.process_api_log(value)
                elif topic == 'application-errors':
                    self.process_error_log(value)
                # Add handlers for other topics as needed
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
            self.running = False
        finally:
            self.close()
    
    def process_api_log(self, log_data):
        """Process an API log message"""
        try:
            logger.debug(f"Processing API log: {log_data}")
            self.db.insert_api_log(log_data)
        except Exception as e:
            logger.error(f"Error processing API log: {e}")
    
    def process_error_log(self, log_data):
        """Process an error log message"""
        try:
            logger.debug(f"Processing error log: {log_data}")
            # Insert into both API logs (for completeness) and error logs (for detailed analysis)
            self.db.insert_api_log(log_data)
            self.db.insert_error_log(log_data)
        except Exception as e:
            logger.error(f"Error processing error log: {e}")
    
    def update_stats_periodically(self):
        """Update statistics tables periodically"""
        while self.running:
            try:
                logger.debug("Updating statistics tables")
                self.db.update_stats()
            except Exception as e:
                logger.error(f"Error updating stats: {e}")
            
            # Update every 5 minutes
            time.sleep(300)
    
    def close(self):
        """Close the consumer"""
        self.running = False
        if self.consumer is not None:
            self.consumer.close()
        logger.info("Kafka consumer closed")