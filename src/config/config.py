from pydantic import BaseModel
from typing import Optional, List
import yaml


class RepoConfig(BaseModel):
    path: str
    name: Optional[str] = None


class Config(BaseModel):
    repos: List[RepoConfig]


def load() -> Config:
    with open("commitiq.yml", "r") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        return Config(**data)
