from fastapi import FastAPI

# Initialize the FastAPI app
app = FastAPI(
    title="Transport Booking API",
    description="Core backend for the transport and logistics platform",
    version="1.0.0"
)

# Health-check endpoint
@app.get("/")
async def root():
    return {
        "status": "API is running", 
        "message": "Krossover Transport API is live."
    }