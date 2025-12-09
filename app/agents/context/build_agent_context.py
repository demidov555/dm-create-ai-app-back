import uuid
from autogen_core.model_context import UnboundedChatCompletionContext
from autogen_core.models import SystemMessage, UserMessage

from app.db import projects
from app.logger.console_logger import info


async def build_agent_context(agent_name: str, project_id: uuid.UUID, task: str):
    project = projects.get_project_by_id(project_id)
    tree = projects.get_structure_cache(project_id)
    summaries = projects.get_file_summaries(project_id)
    memory = projects.get_agent_memory(project_id, agent_name)

    # convert memory into text
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

    # info(system_prompt)

    ctx = UnboundedChatCompletionContext()

    await ctx.add_message(SystemMessage(content=system_prompt))
    await ctx.add_message(UserMessage(content=task, source=agent_name))

    return ctx
