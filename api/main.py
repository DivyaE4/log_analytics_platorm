from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid
from kafka_producer import LogProducer
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Log Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Kafka producer
log_producer = LogProducer(bootstrap_servers=['kafka:29092'])

# Sample data for endpoints
users = [{"id": i, "name": f"User {i}", "email": f"user{i}@example.com"} for i in range(1, 11)]
products = [{"id": i, "name": f"Product {i}", "price": i * 10.0} for i in range(1, 11)]
orders = [{"id": i, "user_id": i % 10 + 1, "product_ids": [i % 10 + 1, (i + 1) % 10 + 1]} for i in range(1, 11)]

# Add middleware to log requests and responses
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Process the request
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        logger.error(f"Request failed: {e}")
        status_code = 500
        response = Response(content=str(e), status_code=status_code)
    
    # Calculate duration
    duration = round((time.time() - start_time) * 1000)
    
    # Get endpoint path
    endpoint = request.url.path
    
    # Prepare log
    log = {
        "request_id": request_id,
        "endpoint": endpoint,
        "method": request.method,
        "status_code": status_code,
        "response_time_ms": duration,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Send to Kafka
    if 400 <= status_code < 600:
        log_producer.send_log("application-errors", log)
    else:
        log_producer.send_log("api-requests", log)
    
    return response

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to Log Analytics API"}

@app.get("/api/users")
async def get_users():
    return users

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    for user in users:
        if user["id"] == user_id:
            return user
    return {"error": "User not found"}, 404

@app.get("/api/products")
async def get_products():
    return products

@app.get("/api/products/{product_id}")
async def get_product(product_id: int):
    for product in products:
        if product["id"] == product_id:
            return product
    return {"error": "Product not found"}, 404

@app.get("/api/orders")
async def get_orders():
    return orders

@app.get("/api/orders/{order_id}")
async def get_order(order_id: int):
    for order in orders:
        if order["id"] == order_id:
            return order
    return {"error": "Order not found"}, 404

@app.post("/api/users")
async def create_user(request: Request):
    data = await request.json()
    return {"id": len(users) + 1, **data}

@app.post("/api/products")
async def create_product(request: Request):
    data = await request.json()
    return {"id": len(products) + 1, **data}

@app.post("/api/orders")
async def create_order(request: Request):
    data = await request.json()
    return {"id": len(orders) + 1, **data}

@app.on_event("shutdown")
def shutdown_event():
    log_producer.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)