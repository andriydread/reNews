import httpx
import trafilatura
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.models.models import ArticleCategory


class AIAnalysisResult(BaseModel):
    summary: str = Field(description="A concise summary (max 200 chars).")
    category: ArticleCategory = Field(description="The best category for this news.")
    language: str = Field(description="Language of the article.")


class AIProcessor:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        reraise=True,
    )
    async def analyze_article(self, title: str, text: str) -> AIAnalysisResult | None:

        prompt = f"""
        You are a high-signal news curator. Analyze this article and provide a JSON response.
        Focus on providing a objective summary and categorization of the news.
        
        Title: {title}
        Content: {text}
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AIAnalysisResult,
                    temperature=0.1,  # Low temperature makes AI more factual and less "creative"
                ),
            )

            if not response.text:
                return None

            # Validate what the AI returned
            return AIAnalysisResult.model_validate_json(response.text)

        except Exception:
            return None
