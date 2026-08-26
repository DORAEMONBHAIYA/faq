import uuid
from datetime import datetime, timedelta
from app.database.mongodb import db

class TaskManager:
    def __init__(self):
        self._use_memory = db is None
        if self._use_memory:
            print("WARNING: TaskManager using in-memory store (MongoDB not connected)")
            self._memory = {}
            self.collection = None
        else:
            self.collection = db.tasks
            self._memory = None

    def create_task(self, user_id: str = None, source_name: str = "Unknown Source", mode: str = "faq", language: str = "auto", source_id: str = None):
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        retention_days = 7 if user_id else 0
        retention_hours = 0 if user_id else 1
        expires_at = datetime.utcnow() + timedelta(days=retention_days, hours=retention_hours)
        task = {
            "task_id": task_id,
            "user_id": user_id,
            "source_id": source_id,
            "source_name": source_name,
            "status": "queued",
            "mode": mode,
            "language": language,
            "result": [],
            "domain": {},
            "agent_trace": [],
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        if self._use_memory:
            self._memory[task_id] = task
        else:
            self.collection.insert_one(task)
        return task_id

    def update(self, task_id, status, result=None, domain=None, trace_entry=None):
        if self._use_memory:
            task = self._memory.get(task_id)
            if not task:
                return
            task["status"] = status
            task["updated_at"] = datetime.utcnow()
            if result is not None:
                task["result"] = result
            if domain is not None:
                task["domain"] = domain
            if trace_entry:
                task.setdefault("agent_trace", []).append({
                    "agent": trace_entry["agent"],
                    "action": trace_entry["action"],
                    "timestamp": datetime.utcnow().isoformat()
                })
            return
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
        if self._use_memory:
            task = self._memory.get(task_id)
            if task:
                return {k: v for k, v in task.items() if k != "_id"}
            return None
        task = self.collection.find_one({"task_id": task_id})
        if task:
            task.pop("_id", None)
            return task
        return None

    def delete_task(self, task_id, user_id):
        if not task_id:
            return False
        if self._use_memory:
            task = self._memory.get(task_id)
            if not task:
                return False
            if user_id and task.get("user_id") != user_id:
                return False
            if not user_id and task.get("user_id") not in (None, ""):
                return False
            del self._memory[task_id]
            return True
        query = {"task_id": task_id}
        if user_id:
            query["user_id"] = user_id
        else:
            query["user_id"] = {"$in": [None, ""]}
        res = self.collection.delete_one(query)
        return res.deleted_count > 0

    def get_user_tasks(self, user_id: str):
        if self._use_memory:
            now = datetime.utcnow()
            tasks = [t for t in self._memory.values() if t.get("user_id") == user_id and t.get("expires_at") > now]
            tasks.sort(key=lambda x: x["created_at"], reverse=True)
            return [{k: v for k, v in t.items() if k != "_id"} for t in tasks]
        return list(self.collection.find(
            {"user_id": user_id, "expires_at": {"$gt": datetime.utcnow()}},
            {"_id": 0}
        ).sort("created_at", -1))

task_manager = TaskManager()
