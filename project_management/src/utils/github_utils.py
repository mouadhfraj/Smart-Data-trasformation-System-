from github import Github
from git import Repo


def create_github_repository(repo_name: str, description: str = "", private: bool = True, github_token: str = None):
    """
    Create a new GitHub repository.
    :param repo_name: Name of the repository.
    :param description: Description of the repository.
    :param private: Whether the repository should be private.
    :param github_token: GitHub token (optional, can be passed as a parameter or resolved from environment variables).
    :return: Repository object.
    """
    if not github_token:
        raise ValueError("GitHub token not provided.")

    try:

        g = Github(github_token)
        user = g.get_user()


        for repo in user.get_repos():
            if repo.name == repo_name:
                raise ValueError(f"Repository '{repo_name}' already exists.")


        repo = user.create_repo(
            name=repo_name,
            description=description,
            private=private,
            auto_init=False
        )
        print(f"Repository '{repo_name}' created successfully: {repo.html_url}")
        return repo
    except Exception as e:
        print(f"Failed to create repository: {e}")
        raise




def push_to_github(repo_dir: str, repo_url: str,  github_token: str = None):
    """
    Push the dbt project to the GitHub repository.
    :param github_token:
    :param repo_dir: Path to the local dbt project directory.
    :param repo_url: URL of the GitHub repository.
    """


    if not github_token:
        raise ValueError("GitHub token not found in environment variables.")


    repo_url_with_token = repo_url.replace("https://", f"https://{github_token}@")


    repo = Repo.init(repo_dir)


    repo.git.add(A=True)


    repo.git.commit(m="Initial commit: dbt project setup")


    repo.create_remote("origin", repo_url_with_token)


    repo.git.push("origin", "HEAD:main")