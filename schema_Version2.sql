-- Tasks: Core task storage
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,     -- 1=high, 4=low
    deadline TEXT,                            -- YYYY-MM-DD
    category TEXT DEFAULT 'other',           -- assignment, exam, etc.
    status TEXT DEFAULT 'pending',           -- pending, in_progress, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Schedule: Time slots assigned to tasks
CREATE TABLE schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    date TEXT NOT NULL,                      -- YYYY-MM-DD
    start_time TEXT NOT NULL,                -- HH:MM
    end_time TEXT NOT NULL,                  -- HH:MM
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Focus Sessions: Camera tracking logs
CREATE TABLE focus_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    total_focused_seconds INTEGER DEFAULT 0,
    total_distracted_seconds INTEGER DEFAULT 0,
    focus_percentage REAL DEFAULT 0.0,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Status Log: Audit trail for task changes
CREATE TABLE status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);