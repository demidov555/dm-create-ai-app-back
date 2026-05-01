import uuid
from langchain_core.messages import HumanMessage, SystemMessage

from app.db import projects


async def build_agent_context(agent_name: str, project_id: uuid.UUID, task: str):
    project = projects.get_project_by_id(project_id)
    tree = projects.get_structure_cache(project_id)
    summaries = projects.get_file_summaries(project_id)
    memory = projects.get_agent_memory(project_id, agent_name)

    memory_text = "\n".join(f"- {k}: {v}" for k, v in memory.items()) or "Нет"

    summaries_text = (
        "\n".join(f"{path}:\n{summary}\n" for path, summary in summaries.items())
        or "Нет файлов"
    )

    meta = f"""
    ID: {project.project_id}
    Название: {project.name}
    Описание: {project.description}
    Статус: {project.status}
    Участники: {project.agent_ids}
    """

    system_prompt = f"""
    ТЕКУЩЕЕ СОСТОЯНИЕ ПРОЕКТА
    =========================

    МЕТА:
    {meta}

    СТРУКТУРА ПРОЕКТА:
    {tree}

    КОРОТКИЕ САММАРИ ФАЙЛОВ:
    {summaries_text}

    ПАМЯТЬ ТВОЕЙ РОЛИ:
    {memory_text}

    ---

    ПРАВИЛА:
    Ты должен выводить JSON строго вида:
    {{
    "create": [...],
    "update": [...],
    "delete": [...]
    }}

    Твоя роль: {agent_name}
    """

    return [SystemMessage(content=system_prompt), HumanMessage(content=task)]
