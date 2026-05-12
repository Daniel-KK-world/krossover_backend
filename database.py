import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

# Get the URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
pool_pre_ping=True # check if connection is alive first 

# Create the engine (the core interface to the database)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a sessionmaker (this creates temporary connections to talk to the DB)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the Base class (all data models will inherit from this)
Base = declarative_base()

# Dependency to get a database session for your API routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()