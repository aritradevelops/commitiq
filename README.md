# CommitIQ

CommitIQ is a CLI tool that turns your git commits into a clean, human-readable summary of what you actually shipped. It scans commits across multiple repositories, filters by your git author identity, and uses AI to translate technical commit messages into product-facing task descriptions — grouped by repo and date.

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A git identity configured (`git config --global user.email`)
- An API key for your chosen AI model provider (see [Supported Models](#supported-models))

## Installation

### Using uv (recommended)

```bash
uv tool install commitiq
```

### Using pip

```bash
pip install commitiq
```

Verify the installation:

```bash
commitiq --help
```

## Supported Models

CommitIQ uses [LiteLLM](https://docs.litellm.ai/) under the hood, so it supports any model that LiteLLM supports. Set the appropriate environment variable for your provider before running:

| Provider | Model example | Environment variable |
|---|---|---|
| OpenAI | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude-haiku-4-5` | `ANTHROPIC_API_KEY` |
| Google | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |

The default model is `gpt-4o-mini`. You can change it at any time with the `use` command.

## API Keys

CommitIQ reads API keys from environment variables. You must set the variable for whichever provider you intend to use **before** running any command that calls the model.

### Setting the key for the current terminal session

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export GEMINI_API_KEY="AIza..."
```

The key is only active for the lifetime of that shell session. Every new terminal window will need the export again unless you persist it.

### Persisting the key across sessions

Add the export line to your shell profile so it is set automatically on login:

```bash
# for zsh (default on macOS)
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
source ~/.zshrc

# for bash
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
source ~/.bashrc
```

### Verifying the key is recognized

Run `commitiq use <model>` without `--no-verify`. CommitIQ will make a minimal test call and report success or a specific auth error:

```bash
commitiq use gpt-4o-mini
# Verifying gpt-4o-mini...
# ✔ Model set to gpt-4o-mini
```

If the key is missing or invalid you will see the provider's error message (e.g. `AuthenticationError: Incorrect API key`). Fix the environment variable and retry.

## User Guide

### 1. Add your repositories

Register the git repos you want CommitIQ to scan:

```bash
commitiq add /path/to/my-project
commitiq add /path/to/another-project --name "Backend API"
```

The `--name` flag sets a display label. If omitted, the directory name is used.

### 2. Set your AI model

```bash
commitiq use gpt-4o-mini
```

CommitIQ will verify the model is reachable before saving. To skip verification (e.g. for local models):

```bash
commitiq use ollama/llama3 --no-verify
```

### 3. Summarize your commits

Summarize commits from the current week (Monday to today):

```bash
commitiq summarize
```

Summarize a custom date range:

```bash
commitiq summarize --since 2025-04-01 --until 2025-04-30
```

Override the model for a single run:

```bash
commitiq summarize --model claude-haiku-4-5
```

### 4. Manage repositories

List all configured repos:

```bash
commitiq list
```

Remove a repo:

```bash
commitiq remove /path/to/my-project
```

## MCP Server

CommitIQ ships a built-in [MCP](https://modelcontextprotocol.io/) server that exposes its functionality as tools any MCP-compatible AI agent can call — Claude Desktop, Cursor, Zed, or any custom agent built with the MCP SDK.

### Starting the server

```bash
commitiq mcp
```

The server runs over **stdio** (standard input/output), which is the transport used by all desktop MCP clients. It stays running in the foreground until you press `Ctrl+C` or send `SIGTERM`.

### Connecting Claude Desktop

Add the following to your Claude Desktop config file.

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "commitiq": {
      "command": "commitiq",
      "args": ["mcp"]
    }
  }
}
```

If `commitiq` is not on your `PATH` (e.g. installed in a uv environment), use the full path to the binary:

```json
{
  "mcpServers": {
    "commitiq": {
      "command": "/Users/you/.local/bin/commitiq",
      "args": ["mcp"]
    }
  }
}
```

Restart Claude Desktop after saving. You should see the commitiq tools listed under the plug icon in the chat input bar.

### Connecting other agents

Any MCP client that supports the stdio transport can connect to CommitIQ. Point the client at:

- **command:** `commitiq`
- **args:** `["mcp"]`

For agents built with the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) or similar, pass the command above as the `StdioServerParameters`.

### Available tools

| Tool | Description |
|---|---|
| `list_repos` | Returns all repos currently tracked by CommitIQ (`path`, `name`). |
| `add_repo(path, name?)` | Adds a repo to the tracked list. `name` is optional. |
| `remove_repo(path)` | Removes a repo from the tracked list. |
| `summarize(since?, until?, model?)` | Summarizes commits as functional tasks. `since`/`until` are `YYYY-MM-DD` (defaults to current week). `model` overrides the saved model for that call. Returns a list of `{date, repos: [{repo, tasks}]}` objects. |

### Example prompts

Once connected, you can ask your agent things like:

- *"What did I work on this week?"*
- *"Summarize my commits for April 2025."*
- *"Add ~/projects/my-app to commitiq and summarize today's work."*

## Configuration

CommitIQ stores its configuration at `~/.commitiq/config.yml`. You don't need to edit it manually, but the format is:

```yaml
repos:
  - path: /absolute/path/to/repo
    name: optional-display-name
model: gpt-4o-mini
```

## License

MIT — see [LICENSE](LICENSE).
