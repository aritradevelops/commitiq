from git import Repo


class GitX:
    def __init__(self, path: str) -> None:
        self.repo = Repo(path)

    def get_commits(self, author: str, since: str, until: str):
        commits = self.repo.iter_commits(
            author=author, since=since, until=until, max_count=100)
        return [c.message for c in commits]
