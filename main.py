from fastapi import FastAPI
from routers import auth, services, bookings 

# Initialize the FastAPI app
app = FastAPI(
    title="Transport Booking API",
    description="Core backend for the transport and logistics platform",
    version="1.0.0"
)

app.include_router(auth.router) # connect the auth router to the main app
app.include_router(services.router) #2. Connecting to the service router 
app.include_router(bookings.router) #3. Connecting to the bookings router

# Health-check endpoint
@app.get("/")
async def root():
    return {
        "status": "API is running", 
        "message": "Krossover Transport API is live."
    }