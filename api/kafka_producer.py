from kafka import KafkaProducer
import json
import logging
import time

logger = logging.getLogger(__name__)

class LogProducer:
    def __init__(self, bootstrap_servers=['localhost:9092']):
        self.producer = None
        self.bootstrap_servers = bootstrap_servers
        self.connect()
        
    def connect(self):
        retries = 5
        while retries > 0:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=3
                )
                logger.info("Connected to Kafka")
                return
            except Exception as e:
                logger.error(f"Failed to connect to Kafka: {e}")
                retries -= 1
                time.sleep(5)
        
        self.producer = None
    
    def send_log(self, topic, log_data):
        if self.producer is None:
            logger.error("Kafka producer not connected")
            self.connect()
            if self.producer is None:
                return False
        
        try:
            future = self.producer.send(topic, log_data)
            future.get(timeout=10)  # Wait for the send to complete
            return True
        except Exception as e:
            logger.error(f"Failed to send log to Kafka: {e}")
            return False
    
    def close(self):
        if self.producer is not None:
            self.producer.flush()
            self.producer.close()
            self.producer = None