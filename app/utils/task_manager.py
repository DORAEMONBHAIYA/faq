import os
import json
import uuid
from threading import Lock

TASK_DIR = "data/tasks"
os.makedirs(TASK_DIR, exist_ok=True)

class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.lock = Lock()

    def create_task(self):
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = {"status": "queued", "result": None}

        with self.lock:
            self.tasks[task_id] = task

        self._persist(task_id, task)
        return task_id

    def update(self, task_id, status, result=None):
        with self.lock:
            if task_id not in self.tasks:
                # Load from disk if needed
                loaded = self._load(task_id)
                if not loaded:
                    raise KeyError(task_id)
                self.tasks[task_id] = loaded

            self.tasks[task_id]["status"] = status
            if result is not None:
                self.tasks[task_id]["result"] = result

        self._persist(task_id, self.tasks[task_id])

    def get(self, task_id):
        if task_id in self.tasks:
            return self.tasks[task_id]

        return self._load(task_id)

    def _persist(self, task_id, data):
        path = os.path.join(TASK_DIR, f"{task_id}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self, task_id):
        path = os.path.join(TASK_DIR, f"{task_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

# ✅ SINGLE GLOBAL INSTANCE
task_manager = TaskManager()
