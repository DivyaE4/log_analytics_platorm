import logging
import time
from kafka_consumer import LogConsumer
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    # Initialize database
    db = Database(
        host="postgres",
        port=5432,
        user="loguser",
        password="1803",
        dbname="loganalytics"
    )
    
    # Create tables if they don't exist
    db.setup()
    
    # Initialize Kafka consumer
    consumer = LogConsumer(
        bootstrap_servers=['kafka:29092'],
        topics=['api-requests', 'api-responses', 'application-errors', 'system-logs'],
        group_id='log-processor',
        db=db
    )
    
    try:
        # Start consuming messages
        logger.info("Starting to consume messages...")
        consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("Stopping consumer...")
    finally:
        consumer.close()
        db.close()

if __name__ == "__main__":
    # Wait for Kafka and Postgres to be ready
    time.sleep(15)
    main()