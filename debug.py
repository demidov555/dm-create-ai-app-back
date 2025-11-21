import os
from github import Github, Auth, GithubException

from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

REPO_NAME = "test-repo-from-pygithub"
DESCRIPTION = "Создано автоматически через PyGithub"
PRIVATE = True

def create_repo(repo_name, description="", private=True):
    """
    Создает репозиторий через PyGithub, используя GH_PAT.
    """
    token = os.getenv("GH_PAT")  # используем отдельную переменную, чтобы не конфликтовать с Codespaces GITHUB_TOKEN

    # Новый способ авторизации
    auth = Auth.Token(token)
    g = Github(auth=auth)

    try:
        user = g.get_user()
        repo = user.create_repo(
            name=repo_name,
            description=description,
            private=private
        )
        return repo.html_url
    except GithubException as e:
        raise RuntimeError(f"Не удалось создать репозиторий: {e}")

# Вызов сразу после запуска
if __name__ == "__main__":
    try:
        url = create_repo(REPO_NAME, DESCRIPTION, PRIVATE)
        print(f"✅ Репозиторий успешно создан: {url}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
