from git import Repo, Git


class GitX:
    def __init__(self, path: str) -> None:
        self.repo = Repo(path)

    def get_commits(self, since: str, until: str):
        author = self._get_author()
        commits = self.repo.iter_commits(
            author=author, since=since, until=until, max_count=100)
        return commits
    
    def _get_author(self):
        with self.repo.config_reader() as conf:
            email = conf.get_value("user", "email", default=None)
        if not email:
            git = Git()
            try:
              email = git.config("--global", "user.email")
            except Exception:
              raise RuntimeError(f"Author not found for repo: {self.repo.working_dir}")
        return email