from litellm import completion, token_counter
from typing import List

_SYSTEM_PROMPT = (
    "You are a product manager reviewing a developer's work log. "
    "Given a list of git commit messages, produce a concise bullet list of "
    "one-line functional tasks — what the product gained or what the user can now do. "
    "Avoid technical jargon (no file names, no function names, no 'refactor'). "
    "Each line should read as a completed action, e.g. 'Added password reset flow'."
)

_CONSOLIDATE_PROMPT = (
    "You are a product manager. Given a list of functional tasks that may have duplicates or overlap, "
    "consolidate them into a clean, deduplicated list of user-facing accomplishments. "
    "Merge related items, remove duplicates, keep the language functional (not technical)."
)

# conservative budget: leaves room for system prompt + response tokens
_TOKEN_BUDGET = 6000


class Summarizer:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    def _count_tokens(self, text: str) -> int:
        try:
            return token_counter(model=self.model, text=text)
        except Exception:
            return len(text) // 4  # rough fallback: ~4 chars per token

    def _chunk_commits(self, commits: List[str]) -> List[List[str]]:
        chunks: List[List[str]] = []
        current: List[str] = []
        current_tokens = 0
        for commit in commits:
            commit_tokens = self._count_tokens(commit)
            if current and current_tokens + commit_tokens >= _TOKEN_BUDGET:
                chunks.append(current)
                current, current_tokens = [commit], commit_tokens
            else:
                current.append(commit)
                current_tokens += commit_tokens
        if current:
            chunks.append(current)
        return chunks

    def _call(self, block: str, system: str) -> List[str]:
        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"{block}\n\nReturn only the task list, one item per line."},
            ],
        )
        raw = response.choices[0].message.content.strip()
        return [line.lstrip("-•* ").strip() for line in raw.splitlines() if line.strip()]

    def summarize(self, commits: List[str]) -> List[str]:
        if not commits:
            return []

        chunks = self._chunk_commits(commits)

        if len(chunks) == 1:
            block = "Commits:\n" + "\n".join(f"- {c}" for c in commits)
            return self._call(block, _SYSTEM_PROMPT)

        # map: summarize each chunk independently
        intermediate: List[str] = []
        for chunk in chunks:
            block = "Commits:\n" + "\n".join(f"- {c}" for c in chunk)
            intermediate.extend(self._call(block, _SYSTEM_PROMPT))

        # reduce: consolidate intermediate tasks into a final deduped list
        block = "Tasks:\n" + "\n".join(f"- {t}" for t in intermediate)
        return self._call(block, _CONSOLIDATE_PROMPT)
