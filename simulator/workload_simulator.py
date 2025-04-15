import requests
import random
import time
import argparse
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# List of endpoints from your API
ENDPOINTS = [
    "/api/users",
    "/api/users/1",
    "/api/users/2",
    "/api/products",
    "/api/products/1",
    "/api/products/2",
    "/api/orders",
    "/api/orders/1",
    "/api/orders/2"
]

METHODS = ["GET", "POST", "PUT", "DELETE"]
# Weight methods - GET more common than other operations
METHOD_WEIGHTS = [0.6, 0.2, 0.15, 0.05]

def send_request(base_url, endpoint, method):
    url = f"{base_url}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json={"data": "sample data"})
        elif method == "PUT":
            response = requests.put(url, json={"data": "updated data"})
        else:  # DELETE
            response = requests.delete(url)
        
        logger.info(f"{method} {url} - Status: {response.status_code}")
        return response.status_code
    except Exception as e:
        logger.error(f"Error with {method} {url}: {e}")
        return 0

def generate_traffic(base_url, rate, duration, error_rate=0.05):
    """
    Generate API traffic.
    
    :param base_url: Base URL of the API
    :param rate: Requests per second
    :param duration: Duration in seconds
    :param error_rate: Probability of generating error-inducing requests
    """
    start_time = time.time()
    request_count = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        while time.time() - start_time < duration:
            target_count = int((time.time() - start_time) * rate)
            
            while request_count < target_count:
                endpoint = random.choice(ENDPOINTS)
                method = random.choices(METHODS, weights=METHOD_WEIGHTS)[0]
                
                # Occasionally send malformed requests to generate errors
                if random.random() < error_rate:
                    # Bad endpoint to generate 404s
                    if random.random() < 0.5:
                        endpoint = f"{endpoint}/nonexistent-{random.randint(1000, 9999)}"
                    # Or use an invalid method for the endpoint
                    else:
                        method = "DELETE"  # Most likely to cause errors on random endpoints
                
                executor.submit(send_request, base_url, endpoint, method)
                request_count += 1
            
            # Sleep a bit to avoid tight loops
            time.sleep(0.01)
    
    logger.info(f"Generated {request_count} requests over {duration} seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API Traffic Generator")
    parser.add_argument("--url", default="http://api:8000", help="Base URL of the API")
    parser.add_argument("--rate", type=float, default=10.0, help="Requests per second")
    parser.add_argument("--duration", type=int, default=3600, help="Duration in seconds")
    parser.add_argument("--error-rate", type=float, default=0.05, help="Error rate (0-1)")
    
    args = parser.parse_args()
    
    logger.info(f"Generating traffic: {args.rate} req/s for {args.duration}s to {args.url}")
    generate_traffic(args.url, args.rate, args.duration, args.error_rate)