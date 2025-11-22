from .deploy_manager import DeployManager


class DeployerService:
    """
    Сервис деплоя, использующий DeployManager.
    """

    def __init__(self, repo_manager):
        self.manager = DeployManager(repo_manager)

    def deploy_pages(self):
        """
        Запуск деплоя GitHub Pages.
        """
        result = self.manager.deploy_github_pages()
        if result["status"] == "ok":
            return f"GitHub Pages deployed: {result['url']}"
        return f"Error deploying GitHub Pages: {result['error']}"

    def deploy_render(self):
        """
        Создание файла render.yaml для Render.
        """
        result = self.manager.deploy_render()
        if result["status"] == "ok":
            return "Render deployment config created."
        return f"Error in Render deploy: {result['error']}"
