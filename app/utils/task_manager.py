import uuid
from datetime import datetime
from app.database.mongodb import db

class TaskManager:
    def __init__(self):
        self.collection = db.tasks

    def create_task(self):
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = {
            "task_id": task_id,
            "status": "queued",
            "result": None,
            "created_at": datetime.utcnow()
        }
        self.collection.insert_one(task)
        return task_id

    def update(self, task_id, status, result=None):
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if result is not None:
            update_data["result"] = result
        
        self.collection.update_one(
            {"task_id": task_id},
            {"$set": update_data}
        )

    def get(self, task_id):
        task = self.collection.find_one({"task_id": task_id})
        if task:
            # Remove MongoDB internal ID for JSON compatibility
            task.pop("_id", None)
            return task
        return None

# ✅ SINGLE GLOBAL INSTANCE
task_manager = TaskManager()
