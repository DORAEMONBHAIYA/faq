import uuid
from datetime import datetime, timedelta
from app.database.mongodb import db

class TaskManager:
    def __init__(self):
        self.collection = db.tasks

    def create_task(self, user_id: str = None, source_name: str = "Unknown Source"):
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Retention Policy
        retention_days = 7 if user_id else 0
        retention_hours = 0 if user_id else 1
        expires_at = datetime.utcnow() + timedelta(days=retention_days, hours=retention_hours)

        task = {
            "task_id": task_id,
            "user_id": user_id,
            "source_name": source_name,
            "status": "queued",
            "result": [],
            "domain": {},
            "agent_trace": [],
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        self.collection.insert_one(task)
        return task_id

    def update(self, task_id, status, result=None, domain=None, trace_entry=None):
        update_doc = {"status": status, "updated_at": datetime.utcnow()}
        
        if result is not None:
            update_doc["result"] = result
        if domain is not None:
            update_doc["domain"] = domain
            
        push_doc = {}
        if trace_entry:
            push_doc["agent_trace"] = {
                "agent": trace_entry["agent"],
                "action": trace_entry["action"],
                "timestamp": datetime.utcnow().isoformat()
            }

        update_query = {"$set": update_doc}
        if push_doc:
            update_query["$push"] = push_doc

        self.collection.update_one({"task_id": task_id}, update_query)

    def get(self, task_id):
        task = self.collection.find_one({"task_id": task_id})
        if task:
            task.pop("_id", None)
            return task
        return None

    def delete_task(self, task_id, user_id):
        """Permanently delete a task and its associated data."""
        # Ensure the task belongs to the user requesting deletion
        res = self.collection.delete_one({"task_id": task_id, "user_id": user_id})
        return res.deleted_count > 0

    def get_user_tasks(self, user_id: str):
        """Retrieve all non-expired tasks for a specific user (including processing ones)."""
        return list(self.collection.find(
            {"user_id": user_id, "expires_at": {"$gt": datetime.utcnow()}},
            {"_id": 0}
        ).sort("created_at", -1))

task_manager = TaskManager()
