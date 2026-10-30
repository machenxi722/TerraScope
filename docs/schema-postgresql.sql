BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> e3a97e4d756a

CREATE TABLE login_attempts (
    key VARCHAR(64) NOT NULL, 
    count INTEGER NOT NULL, 
    window_start FLOAT NOT NULL, 
    PRIMARY KEY (key)
);

CREATE TABLE model_versions (
    id VARCHAR(80) NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    delta_sha256 VARCHAR(64) NOT NULL, 
    base_sha256 VARCHAR(64), 
    preprocess_version VARCHAR(80) NOT NULL, 
    strategies JSONB NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE users (
    username VARCHAR(80) NOT NULL, 
    password_hash TEXT NOT NULL, 
    is_admin BOOLEAN NOT NULL, 
    active BOOLEAN NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (username)
);

CREATE TABLE projects (
    name VARCHAR(120) NOT NULL, 
    description TEXT NOT NULL, 
    created_by VARCHAR(36) NOT NULL, 
    archived BOOLEAN NOT NULL, 
    is_demo BOOLEAN NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE TABLE sessions (
    token_hash VARCHAR(64) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    csrf VARCHAR(64) NOT NULL, 
    expires_at FLOAT NOT NULL, 
    PRIMARY KEY (token_hash), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_sessions_user_id ON sessions (user_id);

CREATE TABLE asset_files (
    project_id VARCHAR(36) NOT NULL, 
    path TEXT NOT NULL, 
    sha256 VARCHAR(64) NOT NULL, 
    size_bytes INTEGER NOT NULL, 
    media_type VARCHAR(80) NOT NULL, 
    filename VARCHAR(180) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    UNIQUE (path)
);

CREATE INDEX ix_asset_files_project_id ON asset_files (project_id);

CREATE TABLE audit_events (
    project_id VARCHAR(36), 
    user_id VARCHAR(36) NOT NULL, 
    action VARCHAR(80) NOT NULL, 
    object_id VARCHAR(80) NOT NULL, 
    details JSONB NOT NULL, 
    request_id VARCHAR(64) NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_audit_events_project_id ON audit_events (project_id);

CREATE TABLE project_members (
    project_id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    PRIMARY KEY (project_id, user_id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE images (
    project_id VARCHAR(36) NOT NULL, 
    name VARCHAR(180) NOT NULL, 
    sample_id VARCHAR(80), 
    split VARCHAR(20) NOT NULL, 
    input_sha256 VARCHAR(64) NOT NULL, 
    width INTEGER NOT NULL, 
    height INTEGER NOT NULL, 
    original_asset_id VARCHAR(36) NOT NULL, 
    display_asset_id VARCHAR(36) NOT NULL, 
    thumbnail_asset_id VARCHAR(36) NOT NULL, 
    label_asset_id VARCHAR(36), 
    coordinate_mode VARCHAR(20) NOT NULL, 
    acquired_at VARCHAR(40), 
    transforms JSONB NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(display_asset_id) REFERENCES asset_files (id), 
    FOREIGN KEY(label_asset_id) REFERENCES asset_files (id), 
    FOREIGN KEY(original_asset_id) REFERENCES asset_files (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(thumbnail_asset_id) REFERENCES asset_files (id), 
    UNIQUE (project_id, input_sha256)
);

CREATE INDEX ix_images_project_id ON images (project_id);

CREATE TABLE analysis_tasks (
    project_id VARCHAR(36) NOT NULL, 
    image_id VARCHAR(36) NOT NULL, 
    created_by VARCHAR(36) NOT NULL, 
    parent_id VARCHAR(36), 
    attempt INTEGER NOT NULL, 
    idempotency_key VARCHAR(120) NOT NULL, 
    request_digest VARCHAR(64) NOT NULL, 
    config JSONB NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    logs JSONB NOT NULL, 
    error JSONB, 
    lease_token VARCHAR(36), 
    lease_until FLOAT NOT NULL, 
    finished_at FLOAT, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(image_id) REFERENCES images (id), 
    FOREIGN KEY(parent_id) REFERENCES analysis_tasks (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    UNIQUE (project_id, idempotency_key)
);

CREATE INDEX ix_analysis_tasks_project_id ON analysis_tasks (project_id);

CREATE INDEX ix_analysis_tasks_status ON analysis_tasks (status);

CREATE TABLE predictions (
    task_id VARCHAR(36) NOT NULL, 
    project_id VARCHAR(36) NOT NULL, 
    image_id VARCHAR(36) NOT NULL, 
    contract JSONB NOT NULL, 
    metrics JSONB NOT NULL, 
    evaluation JSONB, 
    mask_asset_id VARCHAR(36) NOT NULL, 
    overlay_asset_id VARCHAR(36) NOT NULL, 
    layer_asset_id VARCHAR(36) NOT NULL, 
    difference_asset_id VARCHAR(36), 
    gt_layer_asset_id VARCHAR(36), 
    review_revision INTEGER NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(difference_asset_id) REFERENCES asset_files (id), 
    FOREIGN KEY(gt_layer_asset_id) REFERENCES asset_files (id), 
    FOREIGN KEY(image_id) REFERENCES images (id), 
    FOREIGN KEY(layer_asset_id) REFERENCES asset_files (id), 
    FOREIGN KEY(mask_asset_id) REFERENCES asset_files (id), 
    FOREIGN KEY(overlay_asset_id) REFERENCES asset_files (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    FOREIGN KEY(task_id) REFERENCES analysis_tasks (id), 
    UNIQUE (task_id)
);

CREATE INDEX ix_predictions_image_id ON predictions (image_id);

CREATE INDEX ix_predictions_project_id ON predictions (project_id);

CREATE TABLE report_snapshots (
    project_id VARCHAR(36) NOT NULL, 
    prediction_id VARCHAR(36) NOT NULL, 
    created_by VARCHAR(36) NOT NULL, 
    idempotency_key VARCHAR(120) NOT NULL, 
    request_digest VARCHAR(64) NOT NULL, 
    snapshot JSONB NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    files JSONB NOT NULL, 
    error TEXT, 
    lease_token VARCHAR(36), 
    lease_until FLOAT NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(prediction_id) REFERENCES predictions (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id), 
    UNIQUE (project_id, idempotency_key)
);

CREATE INDEX ix_report_snapshots_project_id ON report_snapshots (project_id);

CREATE INDEX ix_report_snapshots_status ON report_snapshots (status);

CREATE TABLE reviews (
    prediction_id VARCHAR(36) NOT NULL, 
    revision INTEGER NOT NULL, 
    created_by VARCHAR(36) NOT NULL, 
    decision VARCHAR(30) NOT NULL, 
    note TEXT NOT NULL, 
    annotations JSONB NOT NULL, 
    id VARCHAR(36) NOT NULL, 
    created_at FLOAT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(prediction_id) REFERENCES predictions (id), 
    UNIQUE (prediction_id, revision)
);

CREATE INDEX ix_reviews_prediction_id ON reviews (prediction_id);

INSERT INTO alembic_version (version_num) VALUES ('e3a97e4d756a') RETURNING alembic_version.version_num;

COMMIT;

