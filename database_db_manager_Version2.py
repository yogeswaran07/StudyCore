"""
Database Manager for Voice AI Study Planner.

Uses SQLite for local, zero-configuration storage.
All task data, schedules, and focus sessions are stored here.

Tables:
    - tasks: All tasks with their metadata
    - schedule: Scheduled time slots for tasks
    - focus_sessions: Focus tracking session logs
"""

import logging
import sqlite3
from datetime import datetime, date
from typing import Optional
from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Handles all database operations for the study planner.

    Uses SQLite with WAL (Write-Ahead Logging) mode for
    better concurrent access performance.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the database manager and create tables if needed.

        Args:
            db_path: Path to the SQLite database file.
                     Defaults to the path in settings.py.
        """
        self.db_path = db_path or str(DATABASE_PATH)
        self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection with optimal settings.

        Returns:
            sqlite3.Connection: Configured database connection.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        conn.execute("PRAGMA foreign_keys=ON")  # Enforce foreign keys
        return conn

    def _create_tables(self) -> None:
        """Create all required tables if they don't exist."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                -- Tasks table: stores all tasks
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 3,
                    deadline TEXT,
                    category TEXT DEFAULT 'other',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Schedule table: stores scheduled time slots
                CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    completed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                        ON DELETE CASCADE
                );

                -- Focus sessions table: logs focus tracking data
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    total_focused_seconds INTEGER DEFAULT 0,
                    total_distracted_seconds INTEGER DEFAULT 0,
                    focus_percentage REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                        ON DELETE SET NULL
                );

                -- Status log table: tracks task state changes
                CREATE TABLE IF NOT EXISTS status_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                        ON DELETE CASCADE
                );

                -- Create indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                    ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_priority
                    ON tasks(priority);
                CREATE INDEX IF NOT EXISTS idx_schedule_date
                    ON schedule(date);
                CREATE INDEX IF NOT EXISTS idx_focus_task
                    ON focus_sessions(task_id);
            """)
            conn.commit()
            logger.info("Database tables created/verified")
        except sqlite3.Error as e:
            logger.error(f"Failed to create tables: {e}")
            raise
        finally:
            conn.close()

    # ──────────────── Task Operations ────────────────

    def add_task(
        self,
        task_name: str,
        priority: int = 3,
        deadline: str = "",
        category: str = "other",
    ) -> int:
        """
        Add a new task to the database.

        Args:
            task_name: Name/description of the task.
            priority: Priority level (1=highest, 4=lowest).
            deadline: Deadline in YYYY-MM-DD format or "unspecified".
            category: Task category (assignment, exam, etc.).

        Returns:
            int: The ID of the newly created task.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO tasks (task_name, priority, deadline, category)
                VALUES (?, ?, ?, ?)
                """,
                (task_name, priority, deadline, category),
            )
            conn.commit()
            task_id = cursor.lastrowid
            logger.info(f"Added task: {task_name} (ID: {task_id})")
            return task_id
        except sqlite3.Error as e:
            logger.error(f"Failed to add task: {e}")
            raise
        finally:
            conn.close()

    def get_pending_tasks(self) -> list[dict]:
        """
        Get all tasks with status 'pending', ordered by priority.

        Returns:
            list[dict]: List of pending tasks.
        """
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT id, task_name, priority, deadline, category, status, created_at
                FROM tasks
                WHERE status = 'pending'
                ORDER BY priority ASC, deadline ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def update_task_status(self, task_id: int, new_status: str) -> None:
        """
        Update the status of a task.

        Args:
            task_id: ID of the task to update.
            new_status: New status (pending, in_progress, completed, cancelled).
        """
        conn = self._get_connection()
        try:
            # Get old status for logging
            row = conn.execute(
                "SELECT status FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            old_status = row["status"] if row else None

            # Update the task
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_status, task_id),
            )

            # Log the status change
            conn.execute(
                """
                INSERT INTO status_log (task_id, old_status, new_status)
                VALUES (?, ?, ?)
                """,
                (task_id, old_status, new_status),
            )

            conn.commit()
            logger.info(f"Task {task_id}: {old_status} → {new_status}")
        finally:
            conn.close()

    def clear_completed_tasks(self) -> int:
        """
        Delete all completed tasks.

        Returns:
            int: Number of tasks deleted.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM tasks WHERE status = 'completed'"
            )
            conn.commit()
            count = cursor.rowcount
            logger.info(f"Cleared {count} completed tasks")
            return count
        finally:
            conn.close()

    # ──────────────── Schedule Operations ────────────────

    def add_schedule_entry(
        self,
        task_id: int,
        date: str,
        start_time: str,
        end_time: str,
    ) -> int:
        """
        Add a scheduled time slot for a task.

        Args:
            task_id: ID of the task.
            date: Date in YYYY-MM-DD format.
            start_time: Start time in HH:MM format.
            end_time: End time in HH:MM format.

        Returns:
            int: ID of the new schedule entry.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO schedule (task_id, date, start_time, end_time)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, date, start_time, end_time),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_today_schedule(self) -> list[dict]:
        """
        Get all scheduled tasks for today.

        Returns:
            list[dict]: Today's scheduled tasks with task details.
        """
        today = date.today().isoformat()
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT s.id, s.start_time, s.end_time, s.completed,
                       t.task_name, t.priority, t.category
                FROM schedule s
                JOIN tasks t ON s.task_id = t.id
                WHERE s.date = ?
                ORDER BY s.start_time ASC
                """,
                (today,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_upcoming_tasks(self, minutes: int = 30) -> list[dict]:
        """
        Get tasks starting within the next N minutes.

        Args:
            minutes: Look-ahead window in minutes.

        Returns:
            list[dict]: Tasks starting soon.
        """
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        future_time = (now + timedelta(minutes=minutes)).strftime("%H:%M")

        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT s.id, s.start_time, s.end_time,
                       t.task_name, t.priority, t.category, t.id as task_id
                FROM schedule s
                JOIN tasks t ON s.task_id = t.id
                WHERE s.date = ?
                  AND s.start_time BETWEEN ? AND ?
                  AND s.completed = 0
                ORDER BY s.start_time ASC
                """,
                (today, current_time, future_time),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # ──────────────── Focus Session Operations ────────────────

    def start_focus_session(self, task_id: int = None) -> int:
        """
        Start a new focus tracking session.

        Args:
            task_id: Optional task ID being worked on.

        Returns:
            int: ID of the new focus session.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO focus_sessions (task_id, start_time)
                VALUES (?, ?)
                """,
                (task_id, datetime.now().isoformat()),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def end_focus_session(
        self,
        session_id: int,
        focused_seconds: int,
        distracted_seconds: int,
    ) -> None:
        """
        End a focus session and record the results.

        Args:
            session_id: ID of the focus session.
            focused_seconds: Total seconds of focus.
            distracted_seconds: Total seconds of distraction.
        """
        total = focused_seconds + distracted_seconds
        focus_pct = (focused_seconds / total * 100) if total > 0 else 0.0

        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE focus_sessions
                SET end_time = ?,
                    total_focused_seconds = ?,
                    total_distracted_seconds = ?,
                    focus_percentage = ?
                WHERE id = ?
                """,
                (
                    datetime.now().isoformat(),
                    focused_seconds,
                    distracted_seconds,
                    round(focus_pct, 1),
                    session_id,
                ),
            )
            conn.commit()
            logger.info(
                f"Focus session {session_id} ended: "
                f"{focus_pct:.1f}% focused"
            )
        finally:
            conn.close()

    def get_focus_stats(self, days: int = 7) -> dict:
        """
        Get aggregated focus statistics for the past N days.

        Args:
            days: Number of days to look back.

        Returns:
            dict: Aggregated focus statistics.
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(total_focused_seconds), 0) as total_focused,
                    COALESCE(SUM(total_distracted_seconds), 0) as total_distracted,
                    COALESCE(AVG(focus_percentage), 0) as avg_focus_pct
                FROM focus_sessions
                WHERE created_at >= ?
                """,
                (cutoff,),
            ).fetchone()
            return dict(row)
        finally:
            conn.close()