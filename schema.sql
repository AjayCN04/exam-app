-- Internal Examination App schema v2 (SQLite / libSQL flavored)
-- Multi-set, multi-exam, multi-attempt design. Safe to re-run: drops and
-- recreates everything, since no real content has been loaded yet.

DROP TABLE IF EXISTS exam_scores;
DROP TABLE IF EXISTS attempt_answers;
DROP TABLE IF EXISTS exam_attempts;
DROP TABLE IF EXISTS exam_module_config;
DROP TABLE IF EXISTS exam_access;
DROP TABLE IF EXISTS exams;
DROP TABLE IF EXISTS answer_key;
DROP TABLE IF EXISTS options;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS question_sets;
DROP TABLE IF EXISTS exam_modules;
DROP TABLE IF EXISTS users;

-- v1 table names that no longer exist under v2 naming
DROP TABLE IF EXISTS participants;
DROP TABLE IF EXISTS attempts;
DROP TABLE IF EXISTS answers;

CREATE TABLE exam_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    order_index INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE question_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_id INTEGER NOT NULL REFERENCES question_sets(id),
    module_id INTEGER REFERENCES exam_modules(id),
    question_text TEXT NOT NULL,
    points INTEGER NOT NULL DEFAULT 1,
    order_index INTEGER NOT NULL,
    -- Multi-select ("select all that apply") vs. single-answer questions.
    is_multi_select INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    option_text TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    -- Authoritative per-option correctness flag; supports 1..N correct
    -- options per question. Source of truth for grading, superseding
    -- answer_key.correct_option_id (kept below only for schema compat).
    is_correct INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE answer_key (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL UNIQUE REFERENCES questions(id),
    correct_option_id INTEGER NOT NULL REFERENCES options(id),
    justification TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_number TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    set_id INTEGER NOT NULL REFERENCES question_sets(id),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    max_attempts INTEGER,
    questions_per_module INTEGER,
    passing_percentage REAL,
    is_closed INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE exam_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    exam_id INTEGER NOT NULL REFERENCES exams(id),
    access_token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, exam_id)
);

-- One row per module included in an exam, with that module's question count.
-- A module with no row for a given exam wasn't selected. Only populated for
-- exams created through the admin UI; exams predating this feature keep
-- using the legacy exams.questions_per_module global column instead.
CREATE TABLE exam_module_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL REFERENCES exams(id),
    module_id INTEGER NOT NULL REFERENCES exam_modules(id),
    question_count INTEGER NOT NULL,
    UNIQUE (exam_id, module_id)
);

CREATE TABLE exam_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_access_id INTEGER NOT NULL REFERENCES exam_access(id),
    attempt_number INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    submitted_at TEXT,
    total_score INTEGER,
    UNIQUE (exam_access_id, attempt_number)
);

CREATE TABLE attempt_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_attempt_id INTEGER NOT NULL REFERENCES exam_attempts(id),
    question_id INTEGER NOT NULL REFERENCES questions(id),
    selected_option_id INTEGER REFERENCES options(id),
    is_correct INTEGER NOT NULL DEFAULT 0,
    -- Comma-joined option ids selected by the participant, populated for
    -- every question (single- or multi-select). selected_option_id above
    -- is still also populated for single-select answers for compatibility.
    selected_option_ids TEXT,
    UNIQUE (exam_attempt_id, question_id)
);

CREATE TABLE exam_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_attempt_id INTEGER NOT NULL UNIQUE REFERENCES exam_attempts(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    exam_id INTEGER NOT NULL REFERENCES exams(id),
    attempt_number INTEGER NOT NULL,
    score INTEGER NOT NULL,
    max_score INTEGER NOT NULL,
    percentage REAL NOT NULL,
    passed INTEGER,
    -- Denormalized copies of users.name / exams.title, kept in sync with user
    -- renames (see app/admin/users.py's user_edit). Exam titles can't be
    -- edited today so exam_name never goes stale, but a future edit-exam
    -- feature would need to cascade-update this column too.
    user_name TEXT,
    exam_name TEXT,
    scored_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_questions_set_id ON questions(set_id);
CREATE INDEX idx_questions_module_id ON questions(module_id);
CREATE INDEX idx_options_question_id ON options(question_id);
CREATE INDEX idx_exam_access_exam_id ON exam_access(exam_id);
CREATE INDEX idx_exam_module_config_exam_id ON exam_module_config(exam_id);
CREATE INDEX idx_exam_attempts_access_id ON exam_attempts(exam_access_id);
CREATE INDEX idx_attempt_answers_attempt_id ON attempt_answers(exam_attempt_id);
CREATE INDEX idx_exam_scores_user_id ON exam_scores(user_id);
CREATE INDEX idx_exam_scores_exam_id ON exam_scores(exam_id);
CREATE INDEX idx_exam_scores_user_exam ON exam_scores(user_id, exam_id);
