import os

import httpx
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.models.models import ArticleCategory


class AIAnalysisResult(BaseModel):
    """Schema to defining the exact JSON structure expected from the AI"""

    summary: str = Field(
        description="A 1-2 sentence (200 character max) summary of the article."
    )
    category: ArticleCategory = Field(
        description="The most appropriate category from the predefined list."
    )
    score: int = Field(
        description="A score from 1 to 10. 1 = useless clickbait. 10 = highly insightful, new tech, or highly valuable knowledge."
    )
    language: str = Field(
        description="The language the article is written in (e.g., 'English', 'Ukrainian')."
    )


class AIProcessor:
    """Service responsible for downloading articles and querying the Gemini AI API."""

    def __init__(self):

        self.client = genai.Client()
        self.model_name = os.getenv("GEMINI_MODEL")

    async def extract_text_from_url(self, url: str):
        """Visits the provided URL, strips away HTML formatting, and returns raw text"""

        try:
            # Headers to mask as browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with httpx.AsyncClient(
                headers=headers, follow_redirects=True
            ) as client:
                response = await client.get(url, timeout=15.0)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Destroy elements that contain useless text
            for element in soup(
                ["script", "style", "nav", "footer", "header", "aside"]
            ):
                element.decompose()

            text = soup.get_text(separator=" ", strip=True)

            # Return only the first 15,000 characters to save input tokens
            return text[:15000]

        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            return None

    async def analyze_article(self, title: str, text: str):
        """Sends the article text to Gemini and forces it to return structured JSON"""

        prompt = f"""
        Analyze the following article.
        Title: {title}
        
        Article Text:
        {text}
        """

        try:
            # Asynchronous requests
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    # Force AI to reply in JSON only
                    response_mime_type="application/json",
                    response_schema=AIAnalysisResult,
                    # Temperature is low for analytical, not creative response
                    temperature=0.2,
                ),
            )

            result = AIAnalysisResult.model_validate_json(response.text)
            return result

        except Exception as e:
            print(f"AI Processing failed: {e}")
            return None
