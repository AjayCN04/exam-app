-- Internal Examination App schema (SQLite / libSQL flavored)

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    access_token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text TEXT NOT NULL,
    points INTEGER NOT NULL DEFAULT 1,
    order_index INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    option_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0,
    order_index INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL UNIQUE REFERENCES participants(id),
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    submitted_at TEXT,
    total_score INTEGER
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id),
    question_id INTEGER NOT NULL REFERENCES questions(id),
    selected_option_id INTEGER REFERENCES options(id),
    is_correct INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_options_question_id ON options(question_id);
CREATE INDEX IF NOT EXISTS idx_answers_attempt_id ON answers(attempt_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_answers_attempt_question ON answers(attempt_id, question_id);
