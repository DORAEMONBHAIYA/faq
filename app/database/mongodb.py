import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("MongoDB")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "aquila_faq"

class MongoDBClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            try:
                # 🌐 Connection for Atlas or Local
                cls._instance.client = MongoClient(
                    MONGODB_URI, 
                    serverSelectionTimeoutMS=5000, # 5s timeout
                    connectTimeoutMS=10000
                )
                # Force a connection check
                cls._instance.client.admin.command('ping')
                cls._instance.db = cls._instance.client[DB_NAME]
                print(f"SUCCESS: Connected to MongoDB at {MONGODB_URI[:20]}...")
            except Exception as e:
                print(f"ERROR: Failed to connect to MongoDB: {e}")
                print("ADVICE: Ensure your MONGODB_URI in .env is correct (Atlas or Local)")
                # We still assign instance to avoid attribute errors, 
                # but operations will fail gracefully with clear errors later
                cls._instance.db = None
        return cls._instance

# Global database access
db = MongoDBClient().db
