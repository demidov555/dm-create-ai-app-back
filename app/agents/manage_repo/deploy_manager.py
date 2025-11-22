from github import GithubException


class DeployManager:
    """
    Низкоуровневый слой деплоя: GitHub Pages + Render.
    """

    def __init__(self, repo_manager):
        self.repo_manager = repo_manager

    # ----------------- GitHub Pages -----------------
    def deploy_github_pages(self):
        """
        Включение GitHub Pages для репозитория.
        """
        try:
            result = self.repo_manager.enable_pages()
            return {
                "status": "ok",
                "url": f"https://{self.repo_manager.USER.login}.github.io/{self.repo_manager.repo_name}",
                "log": result,
            }
        except GithubException as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # ----------------- Render Deploy -----------------
    def deploy_render(self):
        """
        Создание или обновление файла render.yaml.
        """
        try:
            result = self.repo_manager.add_render_yaml()
            return {
                "status": "ok",
                "log": result,
                "note": "Deploy will be handled automatically by Render after push.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
