import os
import logging
from pymongo import MongoClient, ASCENDING
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
                # 🕵️ Debug: Print masked URI
                masked_uri = MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else MONGODB_URI
                print(f"DEBUG: Attempting connection to: ...@{masked_uri}")

                cls._instance.client = MongoClient(
                    MONGODB_URI, 
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000
                )
                cls._instance.client.admin.command('ping')
                cls._instance.db = cls._instance.client[DB_NAME]
                
                # 🛠️ Setup TTL Indexes (7 days = 604800 seconds)
                cls._instance.db.sources.create_index("expires_at", expireAfterSeconds=0)
                cls._instance.db.tasks.create_index("expires_at", expireAfterSeconds=0)
                
                # 🛠️ Setup User Indexes
                cls._instance.db.users.create_index("email", unique=True)
                cls._instance.db.tasks.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
                cls._instance.db.sources.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
                
                print(f"SUCCESS: Connected to MongoDB and initialized TTL indexes.")
            except Exception as e:
                print(f"ERROR: Failed to connect to MongoDB: {e}")
                cls._instance.db = None
        return cls._instance

db = MongoDBClient().db
