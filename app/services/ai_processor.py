import httpx
import trafilatura
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.models import ArticleCategory


class AIAnalysisResult(BaseModel):
    summary: str = Field(description="A concise summary (max 200 chars).")
    category: ArticleCategory = Field(description="The best category for this news.")
    language: str = Field(description="Language of the article.")


class AIProcessor:
    """
    Article analysis pipeline.

    AI integration is currently removed (previously Gemini). analyze_article
    returns a placeholder result so articles are still marked as processed.
    Plug a real provider into analyze_article when one is chosen.
    """

    model_name = "none"

    async def extract_text_from_url(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": settings.USER_AGENT},
                follow_redirects=True,
                timeout=20.0,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            text = trafilatura.extract(response.text, include_comments=False)

            if not text:
                return None

            return text[: settings.MAX_CONTENT_LENGTH]

        except Exception:
            return None

    async def analyze_article(self, title: str, text: str) -> AIAnalysisResult | None:
        # TODO: replace this placeholder with a real AI call
        summary = text[:197] + "..." if len(text) > 200 else text
        return AIAnalysisResult(
            summary=summary,
            category=ArticleCategory.OTHER,
            language="unknown",
        )
