-------------------------------------------------------------------------------
-- KEYSPACE
-------------------------------------------------------------------------------

DROP KEYSPACE IF EXISTS chat_keyspace;

CREATE KEYSPACE chat_keyspace
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

USE chat_keyspace;

-------------------------------------------------------------------------------
-- TABLE: projects
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.projects;

CREATE TABLE chat_keyspace.projects (
    project_id uuid PRIMARY KEY,
    short_id text,
    name text,
    description text,
    status text,
    agent_ids list<text>,
    last_updated timestamp
);

CREATE INDEX IF NOT EXISTS projects_short_id_idx
ON chat_keyspace.projects (short_id);

-------------------------------------------------------------------------------
-- TABLE: project_files (текущее состояние)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.project_files;

CREATE TABLE chat_keyspace.project_files (
    project_id uuid,
    file_path text,
    content text,
    hash text,
    updated_at timestamp,
    PRIMARY KEY (project_id, file_path)
);

-------------------------------------------------------------------------------
-- TABLE: project_file_history (история изменений)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.project_file_history;

CREATE TABLE chat_keyspace.project_file_history (
    project_id uuid,
    file_path text,
    version_time timestamp,
    operation text,
    content_before text,
    content_after text,
    agent text,
    PRIMARY KEY ((project_id, file_path), version_time)
) WITH CLUSTERING ORDER BY (version_time DESC);

-------------------------------------------------------------------------------
-- TABLE: project_structure_cache (дерево репозитория)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.project_structure_cache;

CREATE TABLE chat_keyspace.project_structure_cache (
    project_id uuid PRIMARY KEY,
    tree text,
    updated_at timestamp
);

-------------------------------------------------------------------------------
-- TABLE: project_file_summaries (LLM summary каждого файла)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.project_file_summaries;

CREATE TABLE chat_keyspace.project_file_summaries (
    project_id uuid,
    file_path text,
    summary text,
    updated_at timestamp,
    PRIMARY KEY (project_id, file_path)
);

-------------------------------------------------------------------------------
-- TABLE: agent_project_context (память агентов)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.agent_project_context;

CREATE TABLE chat_keyspace.agent_project_context (
    project_id uuid,
    agent_name text,
    key text,
    value text,
    updated_at timestamp,
    PRIMARY KEY ((project_id, agent_name), key)
);

-------------------------------------------------------------------------------
-- TABLE: agents (пул агентов)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.agents;

CREATE TABLE chat_keyspace.agents (
    agent_id text PRIMARY KEY,
    name text,
    role text
);

-------------------------------------------------------------------------------
-- TABLE: agent_state (состояние агентов внутри проекта)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.agent_state;

CREATE TABLE chat_keyspace.agent_state (
    project_id uuid,
    agent_id text,
    status text,
    current_task text,
    progress int,
    last_updated timestamp,
    PRIMARY KEY (project_id, agent_id)
);

-------------------------------------------------------------------------------
-- TABLE: messages (история диалогов в чанках)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.messages;

CREATE TABLE chat_keyspace.messages (
    project_id uuid,
    bucket text,
    timestamp timeuuid,
    role text,
    message text,
    PRIMARY KEY ((project_id, bucket), timestamp)
) WITH CLUSTERING ORDER BY (timestamp ASC);

-------------------------------------------------------------------------------
-- TABLE: message_buckets (список бакетов для диалогов)
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.message_buckets;

CREATE TABLE chat_keyspace.message_buckets (
    project_id uuid,
    bucket text,
    PRIMARY KEY (project_id, bucket)
);

-------------------------------------------------------------------------------
-- TABLE: project_metrica
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.project_metrica;

CREATE TABLE chat_keyspace.project_metrica (
    project_id uuid PRIMARY KEY,
    progress_percent int,
    progress_last_update timestamp,
    component_counter int,
    code_string_counter int,
    test_coverage_counter int
);

-------------------------------------------------------------------------------
-- TABLE: users
-------------------------------------------------------------------------------

DROP TABLE IF EXISTS chat_keyspace.users;

CREATE TABLE chat_keyspace.users (
    uid text PRIMARY KEY,
    phone text
);

-------------------------------------------------------------------------------
-- DEMO AGENTS
-------------------------------------------------------------------------------

INSERT INTO chat_keyspace.agents (agent_id, name, role)
VALUES ('ProductManager', 'Alice', 'planner');

INSERT INTO chat_keyspace.agents (agent_id, name, role)
VALUES ('Designer', 'Bob', 'designer');

INSERT INTO chat_keyspace.agents (agent_id, name, role)
VALUES ('Frontend', 'Pitter', 'frontend');

INSERT INTO chat_keyspace.agents (agent_id, name, role)
VALUES ('Backend', 'Alex', 'backend');

INSERT INTO chat_keyspace.agents (agent_id, name, role)
VALUES ('QA', 'Anna', 'qa');
