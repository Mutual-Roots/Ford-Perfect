"""Persistente SQLite Task-Queue."""
import sqlite3
import json
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

DB_PATH = Path("/opt/ai-orchestrator/var/queue.db")

@dataclass
class Task:
    prompt: str
    task_type: str = "general_qa"
    attachments: list = field(default_factory=list)
    service: Optional[str] = None   # None = auto-route
    priority: int = 5               # 1=hoch, 10=niedrig
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "pending"
    result: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    attempts: int = 0


class TaskQueue:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    task_type TEXT DEFAULT 'general_qa',
                    attachments TEXT DEFAULT '[]',
                    service TEXT,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    created_at REAL,
                    attempts INTEGER DEFAULT 0
                )
            """)
            con.commit()

    def push(self, task: Task) -> str:
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                task.id, task.prompt, task.task_type,
                json.dumps(task.attachments), task.service,
                task.priority, task.status, task.result,
                task.created_at, task.attempts
            ))
            con.commit()
        return task.id

    def pop(self) -> Optional[Task]:
        """Holt nächsten pending Task (nach Priorität)."""
        with sqlite3.connect(self.db_path) as con:
            row = con.execute("""
                SELECT * FROM tasks
                WHERE status = 'pending'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
            """).fetchone()
            if not row:
                return None
            task = self._row_to_task(row)
            con.execute("UPDATE tasks SET status='running', attempts=attempts+1 WHERE id=?", (task.id,))
            con.commit()
        return task

    def complete(self, task_id: str, result: str):
        with sqlite3.connect(self.db_path) as con:
            con.execute("UPDATE tasks SET status='done', result=? WHERE id=?", (result, task_id))
            con.commit()

    def fail(self, task_id: str, max_attempts: int = 3):
        with sqlite3.connect(self.db_path) as con:
            row = con.execute("SELECT attempts FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row and row[0] >= max_attempts:
                con.execute("UPDATE tasks SET status='failed' WHERE id=?", (task_id,))
            else:
                con.execute("UPDATE tasks SET status='pending' WHERE id=?", (task_id,))
            con.commit()

    def get(self, task_id: str) -> Optional[Task]:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            return self._row_to_task(row) if row else None

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall()
        return dict(rows)

    @staticmethod
    def _row_to_task(row) -> Task:
        return Task(
            id=row[0], prompt=row[1], task_type=row[2],
            attachments=json.loads(row[3]), service=row[4],
            priority=row[5], status=row[6], result=row[7],
            created_at=row[8], attempts=row[9]
        )
