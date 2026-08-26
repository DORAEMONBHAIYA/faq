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
            cls._instance.db = None
            cls._instance.client = None
            cls._instance.is_connected = False
            try:
                if not MONGODB_URI or MONGODB_URI.strip() == "":
                    raise ValueError("MONGODB_URI is empty")
                masked_uri = MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else MONGODB_URI
                print(f"DEBUG: Attempting connection to: ...@{masked_uri}")
                cls._instance.client = MongoClient(
                    MONGODB_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000
                )
                cls._instance.client.admin.command('ping')
                cls._instance.db = cls._instance.client[DB_NAME]
                cls._instance.is_connected = True
                cls._instance.db.sources.create_index("expires_at", expireAfterSeconds=0)
                cls._instance.db.tasks.create_index("expires_at", expireAfterSeconds=0)
                cls._instance.db.users.create_index("email", unique=True)
                cls._instance.db.tasks.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
                cls._instance.db.sources.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
                cls._instance.db.tasks.create_index([("mode", ASCENDING)])
                cls._instance.db.tasks.create_index([("language", ASCENDING)])
                cls._instance.db.sources.create_index([("language", ASCENDING)])
                print(f"SUCCESS: Connected to MongoDB and initialized TTL indexes.")
            except Exception as e:
                print(f"ERROR: Failed to connect to MongoDB: {e}")
                print(f"HINT: Check MONGODB_URI format. Atlas SRV must be mongodb+srv://user:pass@host.mongodb.net/?retryWrites=true&w=majority")
                print(f"HINT: Ensure password is URL-encoded and host exists. Falling back to in-memory store (data will be ephemeral).")
                class InMemoryCursor(list):
                    def sort(self, key, direction=-1):
                        reverse = direction == -1
                        # key can be string or list of tuples
                        if isinstance(key, list):
                            # simple: sort by first key
                            k = key[0][0] if isinstance(key[0], (list, tuple)) else key[0]
                            self[:] = sorted(self, key=lambda x: x.get(k, ""), reverse=reverse)
                        else:
                            self[:] = sorted(self, key=lambda x: x.get(key, ""), reverse=reverse)
                        return self
                class InMemoryCollection:
                    def __init__(self, name):
                        self.name = name
                        self.store = {}
                        self._id_counter = 0
                    def _match(self, doc, filt):
                        if not filt:
                            return True
                        for k, v in filt.items():
                            if isinstance(v, dict):
                                # operator like $gt, $in
                                if "$gt" in v:
                                    if not (doc.get(k) and doc.get(k) > v["$gt"]):
                                        return False
                                elif "$lt" in v:
                                    if not (doc.get(k) and doc.get(k) < v["$lt"]):
                                        return False
                                elif "$in" in v:
                                    if doc.get(k) not in v["$in"]:
                                        return False
                                elif "$gt" in v or "$gte" in v:
                                    # already handled
                                    pass
                                else:
                                    if doc.get(k) != v:
                                        return False
                            else:
                                if doc.get(k) != v:
                                    return False
                        return True
                    def create_index(self, *a, **kw):
                        return
                    def insert_one(self, doc):
                        self._id_counter += 1
                        doc = dict(doc)
                        if "_id" not in doc:
                            doc["_id"] = self._id_counter
                        # use task_id/source_id/email as key if present
                        key = doc.get("task_id") or doc.get("source_id") or doc.get("email") or doc["_id"]
                        self.store[key] = doc
                        class R: inserted_id = key; acknowledged = True
                        return R()
                    def find_one(self, filt, *a, **kw):
                        for d in self.store.values():
                            if self._match(d, filt):
                                return dict(d)
                        return None
                    def find(self, filt, projection=None, *a, **kw):
                        res = [dict(d) for d in self.store.values() if self._match(d, filt)]
                        # apply projection {"_id":0}
                        if projection:
                            for r in res:
                                for k, v in list(projection.items()):
                                    if v == 0 and k in r:
                                        r.pop(k, None)
                        return InMemoryCursor(res)
                    def update_one(self, filt, update, *a, **kw):
                        doc = self.find_one(filt)
                        if not doc:
                            class R: matched_count=0; modified_count=0
                            return R()
                        # get actual stored ref
                        key = doc.get("task_id") or doc.get("source_id") or doc.get("email") or doc.get("_id")
                        stored = self.store[key]
                        if "$set" in update:
                            for k,v in update["$set"].items():
                                stored[k]=v
                        if "$push" in update:
                            for k,v in update["$push"].items():
                                stored.setdefault(k, []).append(v)
                        class R: matched_count=1; modified_count=1
                        return R()
                    def delete_one(self, filt, *a, **kw):
                        doc = self.find_one(filt)
                        if doc:
                            key = doc.get("task_id") or doc.get("source_id") or doc.get("email") or doc.get("_id")
                            self.store.pop(key, None)
                            class R: deleted_count=1
                            return R()
                        class R: deleted_count=0
                        return R()
                class InMemoryDB:
                    def __init__(self):
                        self.users = InMemoryCollection("users")
                        self.tasks = InMemoryCollection("tasks")
                        self.sources = InMemoryCollection("sources")
                cls._instance.db = InMemoryDB()
                cls._instance.is_connected = False
                print("INFO: Using in-memory fallback — data will not persist after restart")
        return cls._instance

_mongo = MongoDBClient()
db = _mongo.db
is_connected = _mongo.is_connected
