CREATE KEYSPACE IF NOT EXISTS chat_keyspace
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE chat_keyspace;

-- Таблица: projects (ProjectInfo)
CREATE TABLE IF NOT EXISTS projects (
  project_id int PRIMARY KEY,
  name text,
  description text,
  status text,
  agent_count int,
  last_updated timestamp
);

-- Таблица: agents
CREATE TABLE IF NOT EXISTS agents (
  project_id int,
  agent_id text,
  name text,
  role text,
  status text,
  current_task text,
  PRIMARY KEY ((project_id), agent_id)
);

-- Таблица: messages
CREATE TABLE IF NOT EXISTS messages (
  project_id int,
  timestamp timeuuid,
  user_id int,
  role text,
  message text,
  PRIMARY KEY ((project_id), timestamp)
);

-- Таблица: project_metrica
CREATE TABLE IF NOT EXISTS project_metrica (
  project_id int PRIMARY KEY,
  progress_percent int,
  progress_last_update timestamp,
  component_counter int,
  code_string_counter int,
  test_coverage_counter int
);

-- Примеры данных
INSERT INTO projects (project_id, name, description, status, agent_count, last_updated)
VALUES (1, 'Мой первый проект', 'Проект по продвижению товаров и услуг', 'active', 4, toTimestamp(now()));

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (1, 'pm-agent', 'Alice', 'planner', 'working', 'Analys bussines system');
VALUES (1, 'designer-agent', 'Alice', 'planner', 'working', 'Designing architecture');
VALUES (1, 'front-agent', 'Pitter', 'planner', 'working', 'Create new home page');
VALUES (1, 'back-agent', 'Alex', 'planner', 'idle', 'Create CRUD api');
VALUES (1, 'tester-agent', 'Anna', 'planner', 'completed', 'Test web interface');

INSERT INTO messages (project_id, user_id, timestamp, role, message)
VALUES (1, 101, now(), 'user', 'Привет, агент!');
VALUES (1, 101, now(), 'agent', 'Привет! Какое приложение я могу собрать для тебя?');
VALUES (1, 101, now(), 'user', 'Я хочу чтобы ты собрал веб приложение по продвижению товаров и услуг');
VALUES (1, 101, now(), 'agent', 'Отлично! могу я уточнить тз?');
VALUES (1, 101, now(), 'user', 'Приложение должно подниматься на angular nodejs сделай минимальный MVP с минималистичным дизайном');

INSERT INTO project_metrica (project_id, progress_percent, progress_last_update, component_counter, code_string_counter, test_coverage_counter)
VALUES (1, 12, toTimestamp(now()), 12, 3400, 78);
