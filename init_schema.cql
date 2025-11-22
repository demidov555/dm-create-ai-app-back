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
    agent_ids list<text>,
    last_updated timestamp
);

CREATE INDEX IF NOT EXISTS projects_short_id_idx ON projects (short_id);

-------------------------------------------------------------------------------
-- TABLE: agents
-------------------------------------------------------------------------------
DROP TABLE IF EXISTS agents;

CREATE TABLE agents (
  agent_id text PRIMARY KEY,
  name text,
  role text,
);

DROP TABLE IF EXISTS agent_state;

CREATE TABLE agent_state (
  project_id uuid,
  agent_id text,
  status text,
  current_task text,
  progress int,
  last_updated timestamp,
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
INSERT INTO agents (agent_id, name, role)
VALUES ('product_manager', 'Alice', 'planner');

INSERT INTO agents (agent_id, name, role)
VALUES ('designer_agent', 'Bob', 'designer agent');

INSERT INTO agents (agent_id, name, role)
VALUES ('frontend', 'Pitter', 'frontend agent');

INSERT INTO agents (agent_id, name, role)
VALUES ('backend', 'Alex', 'backend agent');

INSERT INTO agents (agent_id, name, role)
VALUES ('qa', 'Anna', 'qa dev');
