import click
from gitx import GitX
from datetime import date
from config import load


@click.command()
@click.option("--since", default=date.today())
@click.option("--until", default=date.today())
def commits(since: str, until: str):
    config = load()
    print("config=====>", config)
    for r in config.repos:
        repo = GitX(r.path)
        commits = repo.get_commits(
            "aritrasadhukhan430@gmail.com", since, until)
        print(r.name or 'unknown', "===========>", commits)
