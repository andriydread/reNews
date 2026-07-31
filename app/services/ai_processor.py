import asyncio
import json
import logging

import httpx
import trafilatura
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.core.safe_fetch import fetch_url_safely
from app.models.models import ArticleCategory

logger = logging.getLogger(__name__)


class AIAnalysisResult(BaseModel):
    summary: str = Field(description="A concise summary (max 200 chars).")
    category: ArticleCategory = Field(description="The best category for this news.")
    language: str = Field(description="Language of the article.")


class BatchAnalysisItem(AIAnalysisResult):
    id: int


PROMPT_TEMPLATE = """You are a high-signal news curator. Analyze each article below.

Respond with ONLY a JSON array — no prose, no markdown fences. One object per
article, each with exactly these keys:
  "id": the article id given below, unchanged (integer)
  "summary": objective summary of the article, max 200 characters
  "category": exactly one of: {categories}
  "language": the article's language, e.g. "English"

Articles:
{articles}"""


class AIProcessor:
    """
    Analyzes articles by shelling out to the claude CLI, which authenticates
    via the host's subscription login — no API key. Articles are batched into
    one CLI invocation (settings.AI_BATCH_SIZE) because each spawn is heavy.
    """

    def __init__(self):
        self.model_name = f"claude-{settings.AI_MODEL}"

    def http_client(self) -> httpx.AsyncClient:
        """A client configured for article fetching; the worker shares one
        across a whole scrape phase instead of one per request. Redirects are
        followed by fetch_url_safely so each hop gets an SSRF check."""
        return httpx.AsyncClient(
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=False,
            timeout=20.0,
        )

    async def extract_text_from_url(
        self, url: str, client: httpx.AsyncClient | None = None
    ) -> str | None:
        try:
            if client is not None:
                response = await fetch_url_safely(client, url)
            else:
                async with self.http_client() as own_client:
                    response = await fetch_url_safely(own_client, url)
            response.raise_for_status()

            text = trafilatura.extract(response.text, include_comments=False)

            if not text:
                return None

            return text[: settings.MAX_CONTENT_LENGTH]

        except Exception as exc:
            # info, not warning: paywalled/JS-only pages fail routinely and
            # get a sentinel row — this is telemetry, not an error signal
            logger.info("could not extract %s: %s", url, exc)
            return None

    async def analyze_articles(
        self, items: list[tuple[int, str, str]]
    ) -> dict[int, AIAnalysisResult]:
        """
        Analyze a batch of (article_id, title, text) in one CLI call.

        Returns results keyed by article id. Ids missing from the result
        (CLI failure, unparseable reply, hallucinated id) simply stay pending
        and are retried on the next worker cycle — fail soft, never raise.
        """
        if not items:
            return {}

        raw = await self._run_claude(self._build_prompt(items))
        if raw is None:
            return {}

        return self._parse_reply(raw, expected_ids={item_id for item_id, _, _ in items})

    def _build_prompt(self, items: list[tuple[int, str, str]]) -> str:
        articles = "\n\n".join(
            f"--- article id: {item_id} ---\nTitle: {title}\nContent: {text}"
            for item_id, title, text in items
        )
        categories = ", ".join(f'"{c.value}"' for c in ArticleCategory)
        return PROMPT_TEMPLATE.format(categories=categories, articles=articles)

    async def _run_claude(self, prompt: str) -> str | None:
        """One `claude -p` run; returns the reply text or None on any failure."""
        cmd = [
            settings.CLAUDE_BIN,
            "-p",
            "--model",
            settings.AI_MODEL,
            "--output-format",
            "json",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            logger.error("cannot start claude CLI (%s): %s", settings.CLAUDE_BIN, exc)
            return None

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(prompt.encode()),
                timeout=settings.AI_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.warning("claude CLI timed out after %ss", settings.AI_TIMEOUT_SECONDS)
            return None

        if proc.returncode != 0:
            logger.warning(
                "claude CLI exited %s: %s", proc.returncode, stderr.decode()[:500]
            )
            return None

        # -p --output-format json wraps the reply in an envelope:
        # {"is_error": false, "result": "<reply text>", ...}
        try:
            envelope = json.loads(stdout.decode())
        except ValueError:
            logger.warning("claude CLI stdout was not JSON")
            return None

        if envelope.get("is_error") or "result" not in envelope:
            logger.warning("claude CLI returned an error envelope")
            return None

        return envelope["result"]

    def _parse_reply(
        self, raw: str, expected_ids: set[int]
    ) -> dict[int, AIAnalysisResult]:
        """Extract the JSON array from the reply and validate each entry."""
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end <= start:
            logger.warning("no JSON array in claude reply")
            return {}

        try:
            data = json.loads(raw[start : end + 1])
        except ValueError:
            logger.warning("claude reply array did not parse as JSON")
            return {}

        if not isinstance(data, list):
            return {}

        results: dict[int, AIAnalysisResult] = {}
        for entry in data:
            try:
                item = BatchAnalysisItem.model_validate(entry)
            except ValidationError:
                logger.warning("skipping invalid analysis entry: %.200s", entry)
                continue
            if item.id in expected_ids:
                results[item.id] = item
        return results
