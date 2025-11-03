-- Создание ключспейса
CREATE KEYSPACE IF NOT EXISTS chat_keyspace
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE chat_keyspace;

-- Таблица: projects
DROP TABLE IF EXISTS projects;
CREATE TABLE projects (
  project_id int PRIMARY KEY,
  name text,
  description text,
  status text,
  agent_count int,
  last_updated timestamp
);

-- Таблица: agents
DROP TABLE IF EXISTS agents;
CREATE TABLE agents (
  project_id int,
  agent_id text,
  name text,
  role text,
  status text,
  current_task text,
  PRIMARY KEY ((project_id), agent_id)
);

-- Таблица: messages
DROP TABLE IF EXISTS messages;
CREATE TABLE messages (
  project_id int,
  timestamp timeuuid,
  user_id int,
  role text,
  message text,
  PRIMARY KEY ((project_id), timestamp)
);

-- Таблица: project_metrica
DROP TABLE IF EXISTS project_metrica;
CREATE TABLE project_metrica (
  project_id int PRIMARY KEY,
  progress_percent int,
  progress_last_update timestamp,
  component_counter int,
  code_string_counter int,
  test_coverage_counter int
);

-- Вставка в projects
INSERT INTO projects (project_id, name, description, status, agent_count, last_updated)
VALUES (1, 'Мой первый проект', 'Проект по продвижению товаров и услуг', 'active', 5, toTimestamp(now()));

-- Вставка в agents
INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (1, 'pm-agent', 'Alice', 'planner', 'working', 'Анализ бизнес-системы');

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (1, 'designer-agent', 'Bob', 'designer', 'working', 'Проектирование интерфейса');

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (1, 'front-agent', 'Pitter', 'frontend', 'working', 'Создание домашней страницы');

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (1, 'back-agent', 'Alex', 'backend', 'idle', 'Создание CRUD API');

INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
VALUES (1, 'tester-agent', 'Anna', 'qa', 'completed', 'Тестирование веб-интерфейса');

-- Вставка в messages
INSERT INTO messages (project_id, user_id, timestamp, role, message)
VALUES (1, 101, now(), 'user', 'Привет, агент!');

INSERT INTO messages (project_id, user_id, timestamp, role, message)
VALUES (1, 101, now(), 'agent', 'Привет! Какое приложение я могу собрать для тебя?');

INSERT INTO messages (project_id, user_id, timestamp, role, message)
VALUES (1, 101, now(), 'user', 'Я хочу веб-приложение для продвижения товаров и услуг');

INSERT INTO messages (project_id, user_id, timestamp, role, message)
VALUES (1, 101, now(), 'agent', 'Отлично! Могу я уточнить ТЗ?');

INSERT INTO messages (project_id, user_id, timestamp, role, message)
VALUES (1, 101, now(), 'user', 'Приложение должно быть на Angular и Node.js. Сделай минимальный MVP.');

-- Вставка в project_metrica
INSERT INTO project_metrica (project_id, progress_percent, progress_last_update, component_counter, code_string_counter, test_coverage_counter)
VALUES (1, 12, toTimestamp(now()), 12, 3400, 78);