import asyncio
from app.agents.manage_repo.github_deploy_service import GitHubDeployService
from app.agents.manage_repo.repository_service import RepositoryService
from app.logger.console_logger import info

async def fn():
    project_id: uuid.UUID = "b23c2fa3-3ec2-4803-b0ac-f46a51fc98c3"  # type: ignore
    repo_service = RepositoryService(project_id)
    deploy_service = GitHubDeployService(
        repo_service.manager.token,
        repo_service.manager.user.login,
        repo_service.manager.repo_name or ''
    )

    info(f"{repo_service.manager.user.login}, {repo_service.manager.repo_name}")

    fut = await deploy_service.submit_build(str(project_id), 'frontend', '4a36bde093ad857481805b6c1a9bd5df76b7b94b')
    build_res = await fut

    info(f"{build_res}")

asyncio.run(fn())
