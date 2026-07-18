import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import logging

# Load the environment variables from the .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the URL
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# ─── PRODUCTION-READY ENGINE ─────────────────────────────
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=int(os.getenv("DB_POOL_SIZE", 10)),        # Number of connections to keep
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 20)),  # Extra connections when busy
    pool_pre_ping=True,                                   # Check connection before using
    pool_recycle=3600,                                    # Recycle connections every hour
    echo=False,                                            # Don't log SQL (set True for debugging)
    connect_args={
        "connect_timeout": 15,                            # Connection timeout in seconds
    } if "postgresql" in SQLALCHEMY_DATABASE_URL else {}
)

# ─── SESSIONMAKER ──────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Important for production!
)

# ─── BASE CLASS ────────────────────────────────────────────
Base = declarative_base()

# ─── DEPENDENCY ────────────────────────────────────────────
def get_db():
    """
    Dependency to get a database session for your API routes.
    Properly closes the session after use.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()  # Rollback on error
        raise
    finally:
        db.close()

# ─── OPTIONAL: TEST CONNECTION ON STARTUP ──────────────────
def test_db_connection():
    """Test database connection on startup"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

# ─── OPTIONAL: CREATE TABLES ──────────────────────────────
def create_tables():
    """Create all tables if they don't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created/verified successfully")
    except Exception as e:
        logger.error(f"❌ Table creation failed: {e}")
        raise

# ─── UNCOMMENT TO TEST ON STARTUP ─────────────────────────
# if __name__ == "__main__":
#     test_db_connection()
#     create_tables()