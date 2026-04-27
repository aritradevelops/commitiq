import click
import json
from .config import cfg
from .repo import Repository
from .ai import Summarizer
from concurrent.futures import ThreadPoolExecutor, as_completed
import litellm
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

@click.group()
def cli():
    """entry point for all commands"""

@cli.command()
@click.option("--since", default=None, help="start date (YYYY-MM-DD), defaults to Monday of current week")
@click.option("--until", default=None, help="end date (YYYY-MM-DD), defaults to today")
@click.option("--model", default=None, help="litellm model string (overrides saved model)")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), help="output format (text or json)")
def summarize(since: Optional[str], until: Optional[str], model: Optional[str], output_format: str):
    """summarize commits across all repos as functional tasks, grouped by date then repo"""
    today = date.today()
    since = since or (today - timedelta(days=today.weekday())).isoformat()
    until = until or today.isoformat()
    if not cfg.repos:
        click.echo("No repos configured. Run: commitiq add <path>", err=output_format == "json")
        return

    by_repo: Dict[str, Dict[str, List[str]]] = {}
    for r in cfg.repos:
        repo_name = r.name or r.path
        by_repo[repo_name] = {}
        for c in Repository(r.path).commits(date.fromisoformat(since), date.fromisoformat(until)):
            d = c.authored_datetime.date().isoformat()
            if d not in by_repo[repo_name]:
                by_repo[repo_name][d] = []
            by_repo[repo_name][d].append(str(c.message).strip().splitlines()[0])

    by_repo = {repo: dates for repo, dates in by_repo.items() if dates}

    if not by_repo:
        click.echo("No commits found for the given range.", err=output_format == "json")
        return

    active_model = model or cfg.model
    summarizer = Summarizer(model=active_model)

    # fan out all LLM calls concurrently — one future per (repo, date) pair
    jobs: Dict[Tuple[str, str], List[str]] = {
        (repo_name, d): commits
        for repo_name, dates in by_repo.items()
        for d, commits in dates.items()
    }

    total_commits = sum(len(c) for c in jobs.values())
    click.echo(
        f"Summarizing {click.style(str(total_commits), bold=True)} commit(s) across "
        f"{click.style(str(len(by_repo)), bold=True)} repo(s) · "
        f"{click.style(active_model, fg='cyan')}\n",
        err=output_format == "json",
    )

    results: Dict[Tuple[str, str], List[str]] = {}
    with click.progressbar(
        length=len(jobs), label="  Processing", width=36, show_pos=True,
        file=click.get_text_stream("stderr") if output_format == "json" else None,
    ) as bar:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(summarizer.summarize, commits): key for key, commits in jobs.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    repo_name, d = key
                    click.echo(click.style(f"\n  warning: failed to summarize {repo_name} / {d}: {e}", fg="yellow"), err=True)
                bar.update(1)
    click.echo(err=output_format == "json")

    all_dates = sorted({d for dates in by_repo.values() for d in dates}, reverse=True)

    if output_format == "json":
        output = [
            {
                "date": d,
                "repos": [
                    {"repo": repo_name, "tasks": results.get((repo_name, d), [])}
                    for repo_name in sorted(by_repo)
                    if d in by_repo[repo_name]
                ],
            }
            for d in all_dates
        ]
        click.echo(json.dumps(output, indent=2))
        return

    for d in all_dates:
        click.echo(click.style(f"◆ {d}", bold=True, fg="cyan"))
        for repo_name in sorted(by_repo):
            if d not in by_repo[repo_name]:
                continue
            click.echo(f"  {click.style(repo_name, bold=True)}")
            for task in results.get((repo_name, d), []):
                click.echo(f"    • {task}")
        click.echo()

@cli.command()
@click.argument("model")
@click.option("--no-verify", is_flag=True, help="skip test call (for offline/local models)")
def use(model: str, no_verify: bool):
    """set the default AI model (e.g. gpt-4o-mini, claude-3-haiku-20240307)"""
    if not no_verify:
        click.echo(f"Verifying {model}...")
        try:
            litellm.completion(model=model, messages=[{"role": "user", "content": "hi"}], max_tokens=1)
        except Exception as e:
            click.echo(click.style("✘ Model verification failed: ", fg="red", bold=True) + str(e))
            return
    cfg.set_model(model)
    click.echo(click.style("✔ Model set to ", fg="green", bold=True) + click.style(model, bold=True))

@cli.command(name="list")
def list_repos():
    """list all configured repos"""
    repos = cfg.repos
    if not repos:
        click.echo("No repos configured. Run: commitiq add <path>")
        return
    for r in repos:
        click.echo(click.style(r.name or r.path, bold=True) + click.style(f"  {r.path}", fg="bright_black"))

@cli.command()
@click.argument("path")
def remove(path: str):
    """remove a repo from the list"""
    p = str(Path(path).resolve())
    if not cfg.get_repo(p):
        click.echo(click.style("✘ Repo not found: ", fg="red", bold=True) + p)
        return
    cfg.remove_repo(p)
    click.echo(click.style("✔ Repo removed", fg="green", bold=True) + f"  {p}")

@cli.command(name="mcp")
def mcp_server():
    """Start the MCP server (stdio transport) for use with Claude and other MCP clients."""
    from .mcp_server.server import run
    run()


@cli.command()
@click.argument("path")
@click.option("--name")
def add(path: str, name: Optional[str]):
    """adds the given directory to the repo list"""
    p = Path(path).resolve()
    repo_name = name or p.name
    cfg.add_repo(str(p), repo_name)
    click.echo(click.style("✔ Repo added", fg="green", bold=True) + f"  {click.style(repo_name, bold=True)} → {p}")

