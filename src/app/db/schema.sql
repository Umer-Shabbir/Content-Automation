CREATE TABLE IF NOT EXISTS batches (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
    total_jobs INTEGER DEFAULT 0,
    completed_jobs INTEGER DEFAULT 0,
    failed_jobs INTEGER DEFAULT 0,
    preset_quantities_json TEXT
);

CREATE TABLE IF NOT EXISTS presets (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_builtin BOOLEAN DEFAULT 0,
    output_dir TEXT,
    config_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_profiles (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    base_url TEXT NOT NULL,
    api_key TEXT NOT NULL,
    model TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    preset_id TEXT NOT NULL,
    preset_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_category TEXT,
    last_error TEXT,
    output_directory TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE,
    FOREIGN KEY(preset_id) REFERENCES presets(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS generations (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    preset_name TEXT NOT NULL,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    script TEXT NOT NULL,
    prompts_json TEXT NOT NULL,
    continuity_json TEXT,
    total_words INTEGER DEFAULT 0,
    estimated_duration_sec REAL DEFAULT 0.0,
    quality_score REAL DEFAULT 0.0,
    output_directory TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    CONSTRAINT uq_normalized_title UNIQUE(normalized_title)
);

CREATE TABLE IF NOT EXISTS stage_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    duration_seconds REAL DEFAULT 0.0,
    tokens_used INTEGER DEFAULT 0,
    revisions_count INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT 1,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS generated_ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_name TEXT NOT NULL,
    topic TEXT NOT NULL,
    normalized_topic TEXT NOT NULL,
    title TEXT,
    normalized_title TEXT,
    source TEXT DEFAULT 'preset_pool',
    output_dir TEXT,
    status TEXT DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(normalized_topic)
);

CREATE INDEX IF NOT EXISTS idx_generations_normalized_title ON generations(normalized_title);
CREATE INDEX IF NOT EXISTS idx_jobs_batch_id ON jobs(batch_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_generated_ideas_norm_topic ON generated_ideas(normalized_topic);
CREATE INDEX IF NOT EXISTS idx_generated_ideas_preset ON generated_ideas(preset_name);
CREATE INDEX IF NOT EXISTS idx_generated_ideas_status ON generated_ideas(status);
