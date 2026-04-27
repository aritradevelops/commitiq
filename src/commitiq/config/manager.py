from pydantic import BaseModel
from typing import Optional, List
import yaml
from pathlib import Path


class RepoConfig(BaseModel):
    path: str
    name: Optional[str] = None


class Config(BaseModel):
    repos: List[RepoConfig] = []
    model: str = "gpt-4o-mini"


class ConfigManager:
    _instance = None
    _file_path = Path.home() / ".commitiq" / "config.yml"

    def __init__(self):
        self._config = self._load()

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------
    # Core Load / Save
    # ------------------------

    def _load(self) -> Config:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.touch(exist_ok=True)
        with open(self._file_path, "r") as f:
            data = yaml.safe_load(f) or {}
            return Config(**data)

    def save(self):
        with open(self._file_path, "w") as f:
            yaml.safe_dump(self._config.model_dump(), f)

    # ------------------------
    # Public API
    # ------------------------

    @property
    def repos(self) -> List[RepoConfig]:
        return self._config.repos

    @property
    def model(self) -> str:
        return self._config.model

    def add_repo(self, path: str, name: Optional[str] = None):
        self._config.repos.append(RepoConfig(path=path, name=name))
        self.save()

    def remove_repo(self, path: str):
        self._config.repos = [r for r in self._config.repos if r.path != path]
        self.save()

    def get_repo(self, path: str) -> Optional[RepoConfig]:
        return next((r for r in self._config.repos if r.path == path), None)

    def set_model(self, model: str):
        self._config.model = model
        self.save()