from datetime import date
from typing import Iterator

from git import Commit, Git, Repo


class Repository:
    def __init__(self, path: str) -> None:
        self._repo = Repo(path)
        self._author = self._resolve_author()

    def commits(self, from_date: date, to_date: date) -> Iterator[Commit]:
        return self._repo.iter_commits(
            author=self._author,
            since=f"{from_date.isoformat()} 00:00:00",
            until=f"{to_date.isoformat()} 23:59:59",
        )

    def _resolve_author(self) -> str:
        with self._repo.config_reader() as conf:
            email = conf.get_value("user", "email", default=None)
        if isinstance(email, str) and email:
            return email
        try:
            return Git().config("--global", "user.email")
        except Exception:
            raise RuntimeError(
                f"No git user.email configured locally or globally for: {self._repo.working_dir}"
            )
