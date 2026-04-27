import os
import signal
import sys
from datetime import date, timedelta
from pathlib import Path

import click
from mcp.server.fastmcp import FastMCP

from ..ai import Summarizer
from ..config import cfg
from ..repo import Repository

mcp = FastMCP("commitiq")


@mcp.tool()
def list_repos() -> list[dict]:
    """List all repos configured in commitiq."""
    return [{"path": r.path, "name": r.name or r.path} for r in cfg.repos]


@mcp.tool()
def add_repo(path: str, name: str = "") -> str:
    """Add a repo to commitiq's tracked list."""
    p = str(Path(path).resolve())
    cfg.add_repo(p, name or None)
    return f"Added {name or p}"


@mcp.tool()
def remove_repo(path: str) -> str:
    """Remove a repo from commitiq's tracked list."""
    p = str(Path(path).resolve())
    if not cfg.get_repo(p):
        return f"Repo not found: {p}"
    cfg.remove_repo(p)
    return f"Removed {p}"


@mcp.tool()
def summarize(since: str = "", until: str = "", model: str = "") -> list[dict]:
    """
    Summarize commits across all configured repos as functional tasks.
    since/until: YYYY-MM-DD (defaults to current week Mon to today).
    model: litellm model string (defaults to configured model).
    Returns a list of {repo, date, tasks} objects.
    """
    today = date.today()
    since = since or (today - timedelta(days=today.weekday())).isoformat()
    until = until or today.isoformat()
    active_model = model or cfg.model
    summarizer = Summarizer(model=active_model)

    results = []
    for r in cfg.repos:
        repo_name = r.name or r.path
        by_date: dict[str, list[str]] = {}
        for c in Repository(r.path).commits(date.fromisoformat(since), date.fromisoformat(until)):
            d = c.authored_datetime.date().isoformat()
            by_date.setdefault(d, []).append(str(c.message).strip().splitlines()[0])
        for d, commits in sorted(by_date.items(), reverse=True):
            tasks = summarizer.summarize(commits)
            results.append({"repo": repo_name, "date": d, "tasks": tasks})
    return results


def _log(msg: str = "") -> None:
    print(msg, file=sys.stderr, flush=True)


def run():
    repos = cfg.repos
    model = cfg.model or "(none set)"
    dim = lambda s: click.style(s, fg="bright_black")
    width = 45

    _log()
    _log(f"  {click.style('commitiq', fg='cyan', bold=True)} · MCP server (stdio)")
    _log(f"  {dim('─' * width)}")
    _log(f"  {dim('model')}   {click.style(model, bold=True)}")
    _log(f"  {dim('repos')}   {click.style(str(len(repos)), bold=True)} configured")
    for r in repos:
        label = r.name or r.path
        _log(f"          {click.style('•', fg='cyan')} {click.style(label, bold=True)}  {dim(r.path)}")
    _log(f"  {dim('─' * width)}")
    _log(f"  Press {click.style('Ctrl+C', bold=True)} or send {click.style('SIGTERM', bold=True)} to stop.")
    _log()

    def handle_sigint(signum, frame):
        _log()
        _log(f"  {click.style('Shutting down MCP server... done.', fg='green')}")
        _log()
        os._exit(0)

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)
    mcp.run()

