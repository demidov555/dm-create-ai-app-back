-- Создание keyspace
DROP KEYSPACE IF EXISTS chat_keyspace;
CREATE KEYSPACE IF NOT EXISTS chat_keyspace
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE chat_keyspace;

-------------------------------------------------------------------------------
-- TABLE: projects
-------------------------------------------------------------------------------
DROP TABLE IF EXISTS projects;

CREATE TABLE projects (
    project_id uuid PRIMARY KEY,
    short_id text,
    name text,
    description text,
    status text,
    agent_count int,
    last_updated timestamp
);

-- индекс для поиска по short_id
CREATE INDEX IF NOT EXISTS projects_short_id_idx ON projects (short_id);

-------------------------------------------------------------------------------
-- TABLE: agents
-------------------------------------------------------------------------------
DROP TABLE IF EXISTS agents;

CREATE TABLE agents (
  project_id uuid,
  agent_id text,
  name text,
  role text,
  status text,
  current_task text,
  PRIMARY KEY (project_id, agent_id)
);

-------------------------------------------------------------------------------
-- TABLE: messages
-------------------------------------------------------------------------------
DROP TABLE IF EXISTS messages;

CREATE TABLE messages (
  project_id uuid,
  bucket text,
  timestamp timeuuid,
  role text,
  message text,
  PRIMARY KEY ((project_id, bucket), timestamp)
) WITH CLUSTERING ORDER BY (timestamp ASC);


CREATE TABLE IF NOT EXISTS message_buckets (
    project_id uuid,
    bucket text,
    PRIMARY KEY (project_id, bucket)
);

-------------------------------------------------------------------------------
-- TABLE: project_metrica
-------------------------------------------------------------------------------
DROP TABLE IF EXISTS project_metrica;

CREATE TABLE project_metrica (
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

DROP TABLE IF EXISTS users;

CREATE TABLE users (
  uid text PRIMARY KEY,
  phone text
);

-------------------------------------------------------------------------------
-- Insert demo data for agents
-------------------------------------------------------------------------------
INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (uuid(), 'pm-agent', 'Alice', 'planner', 'working', 'Анализ бизнес-системы');

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (uuid(), 'designer-agent', 'Bob', 'designer', 'working', 'Проектирование интерфейса');

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (uuid(), 'front-agent', 'Pitter', 'frontend', 'working', 'Создание домашней страницы');

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (uuid(), 'back-agent', 'Alex', 'backend', 'idle', 'Создание CRUD API');

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (uuid(), 'tester-agent', 'Anna', 'qa', 'completed', 'Тестирование веб-интерфейса');
